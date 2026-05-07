from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch
from io import StringIO

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.management import call_command

from deals.models import Deal

User = get_user_model()


class AutoReleaseCommandTests(TestCase):
    """Tests for the auto_release management command."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username='autorelease_seller',
            password='sellerpass123',
            email='autorelease_seller@example.com',
            bank_account_number='1234567890',
            bank_code='044',
        )
        self.now = timezone.now()

        # Deal past auto_release_at (should be released)
        self.expired_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Expired Deal',
            amount=Decimal('500.00'),
            buyer_email='expired_buyer@example.com',
            slug='expired-deal-aaa111',
            status='SHIPPED',
            auto_release_at=self.now - timedelta(days=1),
            va_reference='ref-auto-001',
        )

        # Deal not yet past auto_release_at (should be skipped)
        self.future_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Future Deal',
            amount=Decimal('300.00'),
            buyer_email='future_buyer@example.com',
            slug='future-deal-bbb222',
            status='SHIPPED',
            auto_release_at=self.now + timedelta(days=5),
            va_reference='ref-auto-002',
        )

        # Deal that is DISPUTED (should be skipped)
        self.disputed_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Disputed Deal',
            amount=Decimal('200.00'),
            buyer_email='disputed_buyer@example.com',
            slug='disputed-deal-ccc333',
            status='DISPUTED',
            auto_release_at=self.now - timedelta(days=2),
            va_reference='ref-auto-003',
        )

        # Deal in PENDING_PAYMENT status (should be skipped - not SHIPPED)
        self.pending_deal = Deal.objects.create(
            seller=self.seller,
            item_description='Pending Deal',
            amount=Decimal('100.00'),
            buyer_email='pending_buyer@example.com',
            slug='pending-deal-ddd444',
            status='PENDING_PAYMENT',
            auto_release_at=self.now - timedelta(days=3),
            va_reference='ref-auto-004',
        )

    @patch('deals.management.commands.auto_release.payout_seller')
    def test_command_releases_deals_past_auto_release_at(self, mock_payout):
        """Command releases deals past auto_release_at (mock Payaza)."""
        mock_payout.return_value = {'status': 'success'}
        out = StringIO()
        call_command('auto_release', stdout=out)
        output = out.getvalue()

        self.expired_deal.refresh_from_db()
        self.assertEqual(self.expired_deal.status, 'COMPLETED')
        self.assertIsNotNone(self.expired_deal.completed_at)
        mock_payout.assert_called_once_with(self.expired_deal)
        self.assertIn('Released', output)

    @patch('deals.management.commands.auto_release.payout_seller')
    def test_command_skips_deals_not_yet_past_auto_release_at(self, mock_payout):
        """Command skips deals not yet past auto_release_at."""
        mock_payout.return_value = {'status': 'success'}
        call_command('auto_release')

        self.future_deal.refresh_from_db()
        self.assertEqual(self.future_deal.status, 'SHIPPED')
        # Only the expired deal should trigger payout
        mock_payout.assert_called_once()
        mock_payout.assert_called_with(self.expired_deal)

    @patch('deals.management.commands.auto_release.payout_seller')
    def test_command_skips_deals_that_are_disputed(self, mock_payout):
        """Command skips deals that are DISPUTED."""
        mock_payout.return_value = {'status': 'success'}
        call_command('auto_release')

        self.disputed_deal.refresh_from_db()
        self.assertEqual(self.disputed_deal.status, 'DISPUTED')
        # The disputed deal should not be released
        # Only the expired deal should trigger payout
        call_args = mock_payout.call_args_list
        deal_ids = [call[0][0].id for call in call_args]
        self.assertNotIn(self.disputed_deal.id, deal_ids)
