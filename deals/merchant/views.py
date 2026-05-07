from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q
from django.utils.text import slugify
from django.db import transaction
import random
import string

from deals.models import Deal, Transaction
from deals.serializers import DealSerializer, TransactionSerializer
from .serializers import DashboardStatsSerializer, PaymentLinkSerializer


class MerchantDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        deals = Deal.objects.filter(seller=user)

        stats = deals.aggregate(
            total_deals=Count('id'),
            active_deals=Count('id', filter=Q(status__in=['PENDING_PAYMENT', 'PAID', 'SHIPPED'])),
            completed_deals=Count('id', filter=Q(status='COMPLETED')),
            disputed_deals=Count('id', filter=Q(status='DISPUTED')),
            total_revenue=Sum('amount', filter=Q(status='COMPLETED')),
            pending_revenue=Sum('amount', filter=Q(status__in=['PAID', 'SHIPPED'])),
        )

        stats['total_revenue'] = stats['total_revenue'] or 0
        stats['pending_revenue'] = stats['pending_revenue'] or 0

        recent_deals = deals.order_by('-created_at')[:5]

        data = {**stats, 'recent_deals': recent_deals}
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)


class MerchantDealsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DealSerializer

    def get_queryset(self):
        qs = Deal.objects.filter(seller=self.request.user).order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs


class MerchantDealDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DealSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Deal.objects.filter(seller=self.request.user)


class MerchantTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(
            deal__seller=self.request.user
        ).select_related('deal').order_by('-created_at')


class PaymentLinkListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PaymentLinkSerializer
        return PaymentLinkSerializer

    def get_queryset(self):
        return Deal.objects.filter(seller=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        pass

    def create(self, request, *args, **kwargs):
        item_description = request.data.get('item_description')
        amount = request.data.get('amount')
        delivery_days = request.data.get('delivery_days', 3)
        buyer_email = request.data.get('buyer_email', '')
        buyer_phone = request.data.get('buyer_phone', '')

        slug_base = slugify(item_description) or 'link'
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        slug = f"{slug_base}-{suffix}"

        with transaction.atomic():
            deal = Deal.objects.create(
                seller=request.user,
                slug=slug,
                item_description=item_description,
                amount=amount,
                delivery_days=delivery_days,
                buyer_email=buyer_email,
                buyer_phone=buyer_phone,
            )

        link_url = f"https://trustpay.ng/pay/{deal.slug}"
        return Response(PaymentLinkSerializer({
            'id': deal.id,
            'slug': deal.slug,
            'link_url': link_url,
            'item_description': deal.item_description,
            'amount': deal.amount,
            'status': deal.status,
            'created_at': deal.created_at,
            'delivery_days': deal.delivery_days,
        }).data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []
        for deal in queryset:
            link_url = f"https://trustpay.ng/pay/{deal.slug}"
            data.append(PaymentLinkSerializer({
                'id': deal.id,
                'slug': deal.slug,
                'link_url': link_url,
                'item_description': deal.item_description,
                'amount': deal.amount,
                'status': deal.status,
                'created_at': deal.created_at,
                'delivery_days': deal.delivery_days,
            }).data)
        return Response(data)
