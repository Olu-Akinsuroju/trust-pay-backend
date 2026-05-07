from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from deals.models import Deal, Dispute

User = get_user_model()


class DealCreateTests(APITestCase):
    """Tests for deal creation."""

    def setUp(self):
        self.create_url = '/api/deals/'
        self.seller = User.objects.create_user(
            username='seller',
            password='sellerpass123',
            email='seller@example.com',
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            password='buyerpass123',
            email='buyer@example.com',
        )
        self.valid_data = {
            'item_description': 'Test Item',
            'amount': '100.00',
            'delivery_days': 3,
            'buyer_email': 'buyer@example.com',
        }

    def test_authenticated_user_can_create_deal(self):
        """Authenticated user can create a deal (201)."""
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(self.create_url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Deal.objects.count(), 1)
        deal = Deal.objects.first()
        self.assertEqual(deal.seller, self.seller)
        self.assertEqual(deal.item_description, 'Test Item')
        self.assertEqual(deal.amount, Decimal('100.00'))

    def test_unauthenticated_user_cannot_create_deal(self):
        """Unauthenticated user cannot create a deal (401)."""
        response = self.client.post(self.create_url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Deal.objects.count(), 0)

    def test_deal_auto_generates_unique_slug(self):
        """Deal auto-generates unique slug."""
        self.client.force_authenticate(user=self.seller)
        response1 = self.client.post(self.create_url, self.valid_data, format='json')
        response2 = self.client.post(self.create_url, self.valid_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        deals = Deal.objects.filter(seller=self.seller).order_by('created_at')
        self.assertEqual(deals.count(), 2)
        slug1 = deals[0].slug
        slug2 = deals[1].slug
        self.assertNotEqual(slug1, slug2)
        self.assertTrue(slug1.startswith('test-item-'))
        self.assertTrue(slug2.startswith('test-item-'))


class DealListTests(APITestCase):
    """Tests for deal listing."""

    def setUp(self):
        self.list_url = '/api/deals/'
        self.seller = User.objects.create_user(
            username='seller2',
            password='sellerpass123',
            email='seller2@example.com',
        )
        self.other_seller = User.objects.create_user(
            username='other_seller',
            password='otherpass123',
            email='other@example.com',
        )
        self.buyer = User.objects.create_user(
            username='buyer2',
            password='buyerpass123',
            email='buyer2@example.com',
        )
        # Deal where user is seller
        Deal.objects.create(
            seller=self.seller,
            item_description='Seller Deal',
            amount=Decimal('50.00'),
            buyer_email='buyer2@example.com',
            slug='seller-deal-abc123',
            va_reference='ref-list-001',
        )
        # Deal where user is buyer (by email)
        Deal.objects.create(
            seller=self.other_seller,
            item_description='Buyer Deal',
            amount=Decimal('75.00'),
            buyer_email='buyer2@example.com',
            slug='buyer-def456',
            va_reference='ref-list-002',
        )
        # Deal unrelated to user
        Deal.objects.create(
            seller=self.other_seller,
            item_description='Other Deal',
            amount=Decimal('25.00'),
            buyer_email='nobody@example.com',
            slug='other-ghi789',
            va_reference='ref-list-003',
        )

    def test_list_deals_returns_only_users_deals(self):
        """List deals returns only user's deals (as seller or buyer)."""
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_slugs = {d['slug'] for d in response.data}
        self.assertIn('seller-deal-abc123', returned_slugs)
        self.assertIn('buyer-def456', returned_slugs)
        self.assertNotIn('other-ghi789', returned_slugs)


class DealDetailTests(APITestCase):
    """Tests for deal detail endpoint."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller3',
            password='sellerpass123',
            email='seller3@example.com',
        )
        self.pending_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Pending Deal',
            amount=Decimal('100.00'),
            buyer_email='buyer3@example.com',
            slug='pending-xyz111',
            status='PENDING_PAYMENT',
            va_reference='ref-detail-001',
        )
        self.paid_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Paid Deal',
            amount=Decimal('200.00'),
            buyer_email='buyer3@example.com',
            slug='paid-xyz222',
            status='PAID',
            va_reference='ref-detail-002',
        )

    def test_deal_detail_public_when_pending_payment(self):
        """Deal detail is public when status is PENDING_PAYMENT."""
        url = f'/api/deals/{self.pending_deal.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'pending-xyz111')

    def test_deal_detail_requires_auth_when_not_pending_payment(self):
        """Deal detail requires auth when status is not PENDING_PAYMENT."""
        url = f'/api/deals/{self.paid_deal.slug}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DealPayTests(APITestCase):
    """Tests for deal pay endpoint."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller4',
            password='sellerpass123',
            email='seller4@example.com',
        )
        self.pending_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Payable Deal',
            amount=Decimal('150.00'),
            buyer_email='buyer4@example.com',
            slug='payable-aaa111',
            status='PENDING_PAYMENT',
            va_reference='ref-pay-001',
        )
        self.paid_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Already Paid',
            amount=Decimal('150.00'),
            buyer_email='buyer4@example.com',
            slug='paid-bbb222',
            status='PAID',
            va_reference='ref-pay-002',
        )
        self.pay_url = f'/api/deals/{self.pending_deal.slug}/pay/'

    @patch('deals.views.create_virtual_account')
    def test_pay_calls_payaza_and_saves_va_details(self, mock_create_va):
        """Pay endpoint calls Payaza and saves VA details (mock Payaza)."""
        mock_create_va.return_value = {
            'account_number': '1234567890',
            'bank_name': 'Test Bank',
            'reference': 'ref-123',
        }
        response = self.client.post(self.pay_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['va_account_number'], '1234567890')
        self.assertEqual(response.data['va_bank_name'], 'Test Bank')
        self.pending_deal.refresh_from_db()
        self.assertEqual(self.pending_deal.va_account_number, '1234567890')
        self.assertEqual(self.pending_deal.va_bank_name, 'Test Bank')
        self.assertEqual(self.pending_deal.va_reference, 'ref-123')

    def test_pay_returns_400_if_deal_not_pending_payment(self):
        """Pay endpoint returns 400 if deal is not PENDING_PAYMENT."""
        url = f'/api/deals/{self.paid_deal.slug}/pay/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class DealShipTests(APITestCase):
    """Tests for deal ship endpoint."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller5',
            password='sellerpass123',
            email='seller5@example.com',
        )
        self.other_user = User.objects.create_user(
            username='other5',
            password='otherpass123',
            email='other5@example.com',
        )
        self.paid_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Shippable Deal',
            amount=Decimal('100.00'),
            buyer_email='buyer5@example.com',
            slug='shippable-ccc333',
            status='PAID',
            delivery_days=3,
            va_reference='ref-ship-001',
        )
        self.unpaid_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Unpaid Deal',
            amount=Decimal('100.00'),
            buyer_email='buyer5@example.com',
            slug='unpaid-ddd444',
            status='PENDING_PAYMENT',
            delivery_days=3,
            va_reference='ref-ship-002',
        )
        self.ship_url = f'/api/deals/{self.paid_deal.slug}/ship/'

    def test_ship_sets_shipped_status_and_auto_release(self):
        """Ship endpoint sets SHIPPED status and auto_release_at (seller only)."""
        self.client.force_authenticate(user=self.seller)
        before = timezone.now()
        response = self.client.post(self.ship_url)
        after = timezone.now()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.paid_deal.refresh_from_db()
        self.assertEqual(self.paid_deal.status, 'SHIPPED')
        self.assertIsNotNone(self.paid_deal.shipped_at)
        self.assertIsNotNone(self.paid_deal.auto_release_at)
        # auto_release_at should be shipped_at + delivery_days + 1
        expected_delta = timedelta(days=self.paid_deal.delivery_days + 1)
        self.assertAlmostEqual(
            self.paid_deal.auto_release_at - self.paid_deal.shipped_at,
            expected_delta,
            delta=timedelta(seconds=5),
        )

    def test_ship_returns_403_if_not_seller(self):
        """Ship endpoint returns 403 if not the seller."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(self.ship_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ship_returns_400_if_deal_not_paid(self):
        """Ship endpoint returns 400 if deal is not PAID."""
        url = f'/api/deals/{self.unpaid_deal.slug}/ship/'
        self.client.force_authenticate(user=self.seller)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DealConfirmTests(APITestCase):
    """Tests for deal confirm endpoint."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller6',
            password='sellerpass123',
            email='seller6@example.com',
        )
        self.shipped_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Confirmable Deal',
            amount=Decimal('200.00'),
            buyer_email='buyer6@example.com',
            slug='confirmable-eee555',
            status='SHIPPED',
            va_reference='ref-confirm-001',
        )
        self.unshipped_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Not Shipped',
            amount=Decimal('200.00'),
            buyer_email='buyer6@example.com',
            slug='notshipped-fff666',
            status='PAID',
            va_reference='ref-confirm-002',
        )
        self.confirm_url = f'/api/deals/{self.shipped_deal.slug}/confirm/'

    @patch('deals.views.payout_seller')
    def test_confirm_triggers_payout_and_sets_completed(self, mock_payout):
        """Confirm endpoint triggers payout and sets COMPLETED (mock Payaza)."""
        mock_payout.return_value = {'status': 'success'}
        response = self.client.post(self.confirm_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.shipped_deal.refresh_from_db()
        self.assertEqual(self.shipped_deal.status, 'COMPLETED')
        self.assertIsNotNone(self.shipped_deal.completed_at)
        mock_payout.assert_called_once_with(self.shipped_deal)

    def test_confirm_returns_400_if_deal_not_shipped(self):
        """Confirm endpoint returns 400 if deal is not SHIPPED."""
        url = f'/api/deals/{self.unshipped_deal.slug}/confirm/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DealDisputeTests(APITestCase):
    """Tests for deal dispute endpoint."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller7',
            password='sellerpass123',
            email='seller7@example.com',
        )
        self.shipped_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Disputable Deal',
            amount=Decimal('300.00'),
            buyer_email='buyer7@example.com',
            slug='disputable-ggg777',
            status='SHIPPED',
            va_reference='ref-dispute-001',
        )
        self.pending_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Not Disputable',
            amount=Decimal('300.00'),
            buyer_email='buyer7@example.com',
            slug='notdisputable-hhh888',
            status='PENDING_PAYMENT',
            va_reference='ref-dispute-002',
        )
        self.dispute_url = f'/api/deals/{self.shipped_deal.slug}/dispute/'

    def test_dispute_creates_dispute_and_sets_disputed_status(self):
        """Dispute endpoint creates Dispute and sets DISPUTED status."""
        response = self.client.post(self.dispute_url, {
            'reason': 'Item not as described',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.shipped_deal.refresh_from_db()
        self.assertEqual(self.shipped_deal.status, 'DISPUTED')
        self.assertTrue(Dispute.objects.filter(deal=self.shipped_deal).exists())
        dispute = Dispute.objects.get(deal=self.shipped_deal)
        self.assertEqual(dispute.reason, 'Item not as described')
        self.assertEqual(dispute.status, 'OPEN')

    def test_dispute_returns_400_if_deal_already_has_dispute(self):
        """Dispute endpoint returns 400 if deal already has a dispute."""
        # Create first dispute
        Dispute.objects.create(
            deal=self.shipped_deal,
            reason='First dispute',
        )
        self.shipped_deal.status = 'DISPUTED'
        self.shipped_deal.save()
        response = self.client.post(self.dispute_url, {
            'reason': 'Second dispute',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dispute_returns_400_if_deal_status_not_shippable(self):
        """Dispute endpoint returns 400 if deal status is not shippable."""
        url = f'/api/deals/{self.pending_deal.slug}/dispute/'
        response = self.client.post(url, {
            'reason': 'Cannot dispute this',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
