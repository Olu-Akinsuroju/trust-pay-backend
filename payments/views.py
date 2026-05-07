from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.utils import timezone
import json

from deals.models import Deal, Transaction
from payments.payaza import verify_webhook_signature


@api_view(['POST'])
@permission_classes([AllowAny])
def payaza_webhook(request):
    raw_body = request.body
    signature = request.headers.get('X-PAYAZA-SIGN', '')
    if settings.PAYAZA_SECRET and not verify_webhook_signature(raw_body, signature):
        return Response({'error': 'Invalid signature'}, status=401)

    data = json.loads(raw_body)
    reference = data.get('reference') or data.get('transaction_reference')
    if not reference:
        return Response({'error': 'No reference'}, status=400)

    event_type = (data.get('event_type') or data.get('status', '')).lower()

    deal = None
    try:
        deal = Deal.objects.get(va_reference=reference)
    except Deal.DoesNotExist:
        txn = Transaction.objects.filter(payaza_ref=reference).first()
        if txn:
            deal = txn.deal

    if event_type in ('payment.success', 'success', 'completed'):
        if not deal:
            return Response({'status': 'received'})
        deal.status = 'PAID'
        deal.paid_at = timezone.now()
        deal.save()
        Transaction.objects.create(
            deal=deal, tx_type='COLLECTION', status='SUCCESS',
            amount=deal.amount, payaza_ref=data.get('transaction_id', '')
        )

    elif event_type == 'payment.failed':
        if not deal:
            return Response({'status': 'received'})
        Transaction.objects.create(
            deal=deal, tx_type='COLLECTION', status='FAILED',
            amount=deal.amount, payaza_ref=data.get('transaction_id', '')
        )

    elif event_type == 'payout.success':
        if not deal:
            return Response({'status': 'received'})
        Transaction.objects.create(
            deal=deal, tx_type='PAYOUT', status='SUCCESS',
            amount=deal.amount, payaza_ref=data.get('transaction_id', '')
        )

    elif event_type == 'payout.failed':
        if not deal:
            return Response({'status': 'received'})
        Transaction.objects.create(
            deal=deal, tx_type='PAYOUT', status='FAILED',
            amount=deal.amount, payaza_ref=data.get('transaction_id', '')
        )

    return Response({'status': 'received'})
