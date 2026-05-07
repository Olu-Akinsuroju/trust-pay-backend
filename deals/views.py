from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Q
from datetime import timedelta
import random
import string

from .models import Deal, Transaction, Dispute
from .serializers import (
    DealSerializer, DealCreateSerializer,
    DealPayResponseSerializer, TransactionSerializer,
    DisputeSerializer, DisputeCreateSerializer,
)
from payments.payaza import create_virtual_account, payout_seller, refund_buyer, PayazaError


class DealListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return DealCreateSerializer if self.request.method == 'POST' else DealSerializer

    def get_queryset(self):
        return Deal.objects.filter(
            Q(seller=self.request.user) |
            Q(buyer_email=self.request.user.email)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        slug_base = slugify(serializer.validated_data['item_description']) or 'deal'
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        slug = f"{slug_base}-{suffix}"
        serializer.save(seller=self.request.user, slug=slug)


class DealDetailView(generics.RetrieveAPIView):
    queryset = Deal.objects.all()
    lookup_field = 'slug'

    def get_permissions(self):
        slug = self.kwargs.get('slug')
        deal = generics.get_object_or_404(Deal, slug=slug)
        if deal.status == 'PENDING_PAYMENT':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return DealSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def deal_pay(request, slug):
    deal = generics.get_object_or_404(Deal, slug=slug)
    if deal.status != 'PENDING_PAYMENT':
        return Response(
            {'error': 'Deal is not pending payment'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    va = create_virtual_account(deal)
    deal.va_account_number = va['account_number']
    deal.va_bank_name = va['bank_name']
    deal.va_reference = va['reference']
    deal.save()
    return Response(DealPayResponseSerializer({
        'va_account_number': va['account_number'],
        'va_bank_name': va['bank_name'],
        'amount': deal.amount,
    }).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deal_ship(request, slug):
    deal = generics.get_object_or_404(Deal, slug=slug)
    if deal.seller != request.user:
        return Response(
            {'error': 'Only the seller can mark as shipped'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if deal.status != 'PAID':
        return Response(
            {'error': 'Deal must be paid before shipping'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    now = timezone.now()
    deal.status = 'SHIPPED'
    deal.shipped_at = now
    deal.auto_release_at = now + timedelta(days=deal.delivery_days + 1)
    deal.save()
    return Response(DealSerializer(deal).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def deal_confirm(request, slug):
    deal = generics.get_object_or_404(Deal, slug=slug)
    if deal.status != 'SHIPPED':
        return Response(
            {'error': 'Deal must be shipped to confirm'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if hasattr(deal, 'dispute') and deal.dispute.status == 'OPEN':
        return Response(
            {'error': 'Deal is under dispute'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payout_seller(deal)
    except PayazaError:
        Transaction.objects.create(
            deal=deal, tx_type='PAYOUT', status='FAILED', amount=deal.amount
        )
        return Response(
            {'error': 'Payout failed, please try again'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    deal.status = 'COMPLETED'
    deal.completed_at = timezone.now()
    deal.save()
    Transaction.objects.create(
        deal=deal, tx_type='PAYOUT', status='SUCCESS', amount=deal.amount
    )
    return Response(DealSerializer(deal).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def deal_dispute(request, slug):
    deal = generics.get_object_or_404(Deal, slug=slug)
    if deal.status not in ('SHIPPED', 'DELIVERED', 'PAID'):
        return Response(
            {'error': 'Cannot dispute this deal'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = DisputeCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if hasattr(deal, 'dispute'):
        return Response(
            {'error': 'Deal already has a dispute'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    with transaction.atomic():
        Dispute.objects.create(deal=deal, reason=serializer.validated_data['reason'])
        deal.status = 'DISPUTED'
        deal.save()
    return Response({'dispute_id': deal.dispute.id, 'status': 'OPEN'})
