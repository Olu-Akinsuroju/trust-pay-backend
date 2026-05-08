import json
import hmac
import hashlib
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from deals.models import Deal, Transaction
from payments.payaza import PayazaError, create_virtual_account, payout_seller

User = get_user_model()

PAYAZA_SECRET = 'test-webhook-secret'


def generate_webhook_signature(body, secret=PAYAZA_SECRET):
    """Generate a valid Payaza webhook signature."""
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return expected


@override_settings(PAYAZA_SECRET=PAYAZA_SECRET)
class PayazaWebhookTests(APITestCase):
    """Tests for Payaza webhook endpoint."""

    def setUp(self):
        self.webhook_url = '/api/webhooks/payaza/'
        self.seller = User.objects.create_user(
            username='webhook_seller',
            password='sellerpass123',
            email='webhook_seller@example.com',
        )
        self.deal = Deal.objects.create(
            seller=self.seller,
            item_description='Webhook Deal',
            amount=Decimal('500.00'),
            buyer_email='webhook_buyer@example.com',
            slug='webhook-deal-abc123',
            status='PENDING_PAYMENT',
            va_reference='ref-webhook-001',
        )

    def _make_webhook_request(self, data, signature=None, valid_sig=True):
        """Helper to make webhook requests."""
        body = json.dumps(data).encode('utf-8')
        if valid_sig and signature is None:
            signature = generate_webhook_signature(body)
        elif signature is None:
            signature = 'invalid-signature'
        return self.client.post(
            self.webhook_url,
            data=body,
            content_type='application/json',
            HTTP_X_PAYAZA_SIGN=signature,
        )

    def test_webhook_with_valid_signature_processes_payment_success(self):
        """Webhook with valid signature processes payment.success event."""
        data = {
            'event_type': 'payment.success',
            'reference': 'ref-webhook-001',
            'transaction_id': 'txn-12345',
        }
        response = self._make_webhook_request(data, valid_sig=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.status, 'PAID')
        self.assertIsNotNone(self.deal.paid_at)
        self.assertTrue(
            Transaction.objects.filter(
                deal=self.deal,
                tx_type='COLLECTION',
                status='SUCCESS',
                payaza_ref='txn-12345',
            ).exists()
        )

    def test_webhook_with_invalid_signature_returns_401(self):
        """Webhook with invalid signature returns 401."""
        data = {
            'event_type': 'payment.success',
            'reference': 'ref-webhook-001',
        }
        response = self._make_webhook_request(data, valid_sig=False)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_webhook_with_unknown_reference_returns_response(self):
        """Webhook with unknown reference returns appropriate response."""
        data = {
            'event_type': 'payment.success',
            'reference': 'unknown-ref-999',
        }
        response = self._make_webhook_request(data, valid_sig=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'received')

    def test_webhook_handles_payment_failed_event(self):
        """Webhook handles payment.failed event (creates FAILED transaction)."""
        data = {
            'event_type': 'payment.failed',
            'reference': 'ref-webhook-001',
            'transaction_id': 'txn-failed-001',
        }
        response = self._make_webhook_request(data, valid_sig=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Transaction.objects.filter(
                deal=self.deal,
                tx_type='COLLECTION',
                status='FAILED',
                payaza_ref='txn-failed-001',
            ).exists()
        )

    def test_webhook_handles_payout_success_event(self):
        """Webhook handles payout.success event (creates PAYOUT transaction)."""
        # First mark deal as paid so we have a reference for payout
        self.deal.status = 'PAID'
        self.deal.save()
        data = {
            'event_type': 'payout.success',
            'reference': 'ref-webhook-001',
            'transaction_id': 'txn-payout-001',
        }
        response = self._make_webhook_request(data, valid_sig=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Transaction.objects.filter(
                deal=self.deal,
                tx_type='PAYOUT',
                status='SUCCESS',
                payaza_ref='txn-payout-001',
            ).exists()
        )


@override_settings(PAYAZA_MOCK_MODE=False)
class PayazaServiceTests(TestCase):
    """Tests for Payaza service functions."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='payaza_seller',
            password='sellerpass123',
            email='payaza_seller@example.com',
            bank_account_number='1234567890',
            bank_code='044',
        )
        self.deal = Deal.objects.create(
            seller=self.seller,
            item_description='Payaza Test Deal',
            amount=Decimal('1000.00'),
            buyer_email='payaza_buyer@example.com',
            slug='payaza-test-xyz789',
            status='PENDING_PAYMENT',
            trust_fee_percent=Decimal('1.50'),
            va_reference='ref-payaza-svc-001',
        )

    @patch('payments.payaza.requests.post')
    def test_create_virtual_account_returns_correct_structure(self, mock_post):
        """create_virtual_account returns correct data structure (mock requests)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'account_number': '9876543210',
            'bank_name': 'Access Bank',
            'reference': 'ref-va-001',
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = create_virtual_account(self.deal)

        self.assertEqual(result['account_number'], '9876543210')
        self.assertEqual(result['bank_name'], 'Access Bank')
        self.assertEqual(result['reference'], 'ref-va-001')
        mock_post.assert_called_once()

    @patch('payments.payaza.requests.post')
    def test_create_virtual_account_raises_payaza_error_on_failure(self, mock_post):
        """PayazaError is raised on request failure (mock requests)."""
        import requests as req
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        error = req.RequestException('Request failed')
        error.response = mock_response
        mock_post.side_effect = error

        with self.assertRaises(PayazaError) as context:
            create_virtual_account(self.deal)

        self.assertIn('Failed to create virtual account', str(context.exception))
        self.assertEqual(context.exception.status_code, 500)

    @patch('payments.payaza.requests.post')
    def test_payout_seller_calculates_correct_net_amount(self, mock_post):
        """payout_seller calculates correct net amount with fee (mock requests)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'success', 'transaction_id': 'payout-001'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = payout_seller(self.deal)

        # Verify the amount sent: 1000 - (1000 * 1.5 / 100) = 985.00
        call_kwargs = mock_post.call_args[1]
        sent_amount = call_kwargs['json']['amount']
        self.assertEqual(Decimal(sent_amount), Decimal('985.00'))
        self.assertEqual(result['status'], 'success')

    @patch('payments.payaza.requests.post')
    def test_payout_seller_raises_payaza_error_on_failure(self, mock_post):
        """PayazaError is raised on payout failure (mock requests)."""
        import requests as req
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        error = req.RequestException('Payout failed')
        error.response = mock_response
        mock_post.side_effect = error

        with self.assertRaises(PayazaError) as context:
            payout_seller(self.deal)

        self.assertIn('Failed to process payout', str(context.exception))
        self.assertEqual(context.exception.status_code, 400)
