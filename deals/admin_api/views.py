from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils import timezone

from deals.models import Dispute, Deal, Transaction
from deals.serializers import AdminDisputeSerializer, DealSerializer
from payments.payaza import refund_buyer, payout_seller


class DisputeListView(generics.ListAPIView):
    queryset = Dispute.objects.filter(status='OPEN').select_related('deal').order_by('-created_at')
    serializer_class = AdminDisputeSerializer
    permission_classes = [IsAdminUser]


class DisputeResolveView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        dispute = generics.get_object_or_404(
            Dispute.objects.select_related('deal'), pk=pk
        )
        if dispute.status != 'OPEN':
            return Response(
                {'error': 'Dispute is already resolved'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get('action')
        if action == 'refund':
            refund_buyer(dispute.deal)
            dispute.status = 'RESOLVED_REFUND'
            dispute.deal.status = 'REFUNDED'
            Transaction.objects.create(
                deal=dispute.deal, tx_type='REFUND', status='SUCCESS',
                amount=dispute.deal.amount,
            )
        elif action == 'release':
            payout_seller(dispute.deal)
            dispute.status = 'RESOLVED_RELEASE'
            dispute.deal.status = 'COMPLETED'
            dispute.deal.completed_at = timezone.now()
            Transaction.objects.create(
                deal=dispute.deal, tx_type='PAYOUT', status='SUCCESS',
                amount=dispute.deal.amount,
            )
        else:
            return Response(
                {'error': 'action must be "refund" or "release"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dispute.resolved_at = timezone.now()
        dispute.deal.save()
        dispute.save()

        return Response({
            'dispute': AdminDisputeSerializer(dispute).data,
            'deal': DealSerializer(dispute.deal).data,
        })
