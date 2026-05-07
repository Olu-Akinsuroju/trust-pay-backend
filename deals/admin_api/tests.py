from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from deals.models import Deal, Dispute

User = get_user_model()


class AdminDisputeListTests(APITestCase):
    """Tests for admin dispute list endpoint."""

    def setUp(self):
        self.list_url = '/api/admin/disputes/'
        self.staff_user = User.objects.create_user(
            username='admin_staff',
            password='adminpass123',
            email='admin@example.com',
            is_staff=True,
        )
        self.non_staff_user = User.objects.create_user(
            username='regular_user',
            password='userpass123',
            email='regular@example.com',
            is_staff=False,
        )
        self.seller = User.objects.create_user(
            username='dispute_seller',
            password='sellerpass123',
            email='dispute_seller@example.com',
        )
        self.deal = Deal.objects.create(
            seller=self.seller,
            item_description='Disputed Deal',
            amount=Decimal('500.00'),
            buyer_email='dispute_buyer@example.com',
            slug='disputed-deal-aaa111',
            status='DISPUTED',
            va_reference='ref-admin-001',
        )
        self.open_dispute = Dispute.objects.create(
            deal=self.deal,
            reason='Item not received',
            status='OPEN',
        )
        # Also create a resolved dispute to verify filtering
        self.deal2 = Deal.objects.create(
            seller=self.seller,
            item_description='Resolved Deal',
            amount=Decimal('300.00'),
            buyer_email='dispute_buyer@example.com',
            slug='resolved-deal-bbb222',
            status='COMPLETED',
            va_reference='ref-admin-002',
        )
        self.resolved_dispute = Dispute.objects.create(
            deal=self.deal2,
            reason='Quality issue',
            status='RESOLVED_REFUND',
        )

    def test_staff_user_can_list_open_disputes(self):
        """Staff user can list open disputes."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.open_dispute.id))

    def test_non_staff_user_cannot_list_disputes(self):
        """Non-staff user cannot list disputes (403)."""
        self.client.force_authenticate(user=self.non_staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminDisputeResolveTests(APITestCase):
    """Tests for admin dispute resolve endpoint."""

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='resolve_admin',
            password='adminpass123',
            email='resolve_admin@example.com',
            is_staff=True,
        )
        self.seller = User.objects.create_user(
            username='resolve_seller',
            password='sellerpass123',
            email='resolve_seller@example.com',
            bank_account_number='1234567890',
            bank_code='044',
        )
        self.deal = Deal.objects.create(
            seller=self.seller,
            item_description='Resolve Deal',
            amount=Decimal('1000.00'),
            buyer_email='resolve_buyer@example.com',
            slug='resolve-deal-ccc333',
            status='DISPUTED',
            va_reference='ref-resolve-001',
        )
        self.open_dispute = Dispute.objects.create(
            deal=self.deal,
            reason='Buyer claims item not as described',
            status='OPEN',
        )
        self.resolve_url = f'/api/admin/disputes/{self.open_dispute.id}/resolve/'

    @patch('deals.admin_api.views.refund_buyer')
    def test_staff_can_resolve_dispute_with_refund(self, mock_refund):
        """Staff user can resolve dispute with action=refund."""
        mock_refund.return_value = {'status': 'success'}
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.resolve_url, {
            'action': 'refund',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.open_dispute.refresh_from_db()
        self.assertEqual(self.open_dispute.status, 'RESOLVED_REFUND')
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.status, 'REFUNDED')
        self.assertIsNotNone(self.open_dispute.resolved_at)
        mock_refund.assert_called_once_with(self.deal)

    @patch('deals.admin_api.views.payout_seller')
    def test_staff_can_resolve_dispute_with_release(self, mock_payout):
        """Staff user can resolve dispute with action=release."""
        mock_payout.return_value = {'status': 'success'}
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.resolve_url, {
            'action': 'release',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.open_dispute.refresh_from_db()
        self.assertEqual(self.open_dispute.status, 'RESOLVED_RELEASE')
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.status, 'COMPLETED')
        self.assertIsNotNone(self.deal.completed_at)
        self.assertIsNotNone(self.open_dispute.resolved_at)
        mock_payout.assert_called_once_with(self.deal)

    def test_resolving_already_resolved_dispute_returns_400(self):
        """Resolving already-resolved dispute returns 400."""
        self.open_dispute.status = 'RESOLVED_REFUND'
        self.open_dispute.save()
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.resolve_url, {
            'action': 'refund',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_action_returns_400(self):
        """Invalid action returns 400."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(self.resolve_url, {
            'action': 'invalid_action',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
