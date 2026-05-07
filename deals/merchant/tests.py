from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from deals.models import Deal, Transaction

User = get_user_model()


class MerchantDashboardTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller1', password='pass1234', email='seller@test.com'
        )
        self.buyer_email = 'buyer@test.com'
        self.client.force_authenticate(user=self.seller)
        self.url = reverse('merchant-dashboard')

    def _create_deal(self, status='PENDING_PAYMENT', amount='5000.00'):
        return Deal.objects.create(
            seller=self.seller,
            slug=f'deal-{status}-{amount}',
            item_description='Test Item',
            amount=amount,
            delivery_days=3,
            buyer_email=self.buyer_email,
            status=status,
        )

    def test_dashboard_returns_stats(self):
        self._create_deal('PENDING_PAYMENT', '1000.00')
        self._create_deal('PAID', '2000.00')
        self._create_deal('SHIPPED', '3000.00')
        completed = self._create_deal('COMPLETED', '5000.00')
        self._create_deal('DISPUTED', '1500.00')

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_deals'], 5)
        self.assertEqual(response.data['active_deals'], 3)
        self.assertEqual(response.data['completed_deals'], 1)
        self.assertEqual(response.data['disputed_deals'], 1)
        self.assertEqual(response.data['total_revenue'], '5000.00')
        self.assertEqual(response.data['pending_revenue'], '5000.00')
        self.assertEqual(len(response.data['recent_deals']), 5)

    def test_dashboard_empty_seller(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_deals'], 0)
        self.assertEqual(response.data['total_revenue'], '0.00')

    def test_dashboard_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_only_shows_own_deals(self):
        other_seller = User.objects.create_user(
            username='seller2', password='pass1234'
        )
        Deal.objects.create(
            seller=other_seller, slug='other-deal',
            item_description='Other', amount='100.00',
            delivery_days=1, status='COMPLETED'
        )
        self._create_deal('COMPLETED', '500.00')

        response = self.client.get(self.url)
        self.assertEqual(response.data['total_deals'], 1)
        self.assertEqual(response.data['completed_deals'], 1)


class MerchantDealsTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller1', password='pass1234', email='seller@test.com'
        )
        self.client.force_authenticate(user=self.seller)
        self.url = reverse('merchant-deals')

        Deal.objects.create(
            seller=self.seller, slug='deal-paid',
            item_description='Paid Item', amount='1000.00',
            delivery_days=2, buyer_email='buyer@test.com', status='PAID'
        )
        Deal.objects.create(
            seller=self.seller, slug='deal-completed',
            item_description='Completed Item', amount='2000.00',
            delivery_days=3, buyer_email='buyer@test.com', status='COMPLETED'
        )

    def test_list_all_deals(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 2)

    def test_filter_by_status(self):
        response = self.client.get(self.url, {'status': 'PAID'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'PAID')

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MerchantDealDetailTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller1', password='pass1234'
        )
        self.other = User.objects.create_user(
            username='seller2', password='pass1234'
        )
        self.deal = Deal.objects.create(
            seller=self.seller, slug='my-deal',
            item_description='My Item', amount='500.00',
            delivery_days=1, status='PAID'
        )
        self.url = reverse('merchant-deal-detail', kwargs={'slug': 'my-deal'})

    def test_seller_can_view_own_deal(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['slug'], 'my-deal')

    def test_other_seller_cannot_view_deal(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MerchantTransactionsTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller1', password='pass1234'
        )
        self.client.force_authenticate(user=self.seller)
        self.deal = Deal.objects.create(
            seller=self.seller, slug='tx-deal',
            item_description='Tx Item', amount='1000.00',
            delivery_days=1, status='PAID'
        )
        Transaction.objects.create(
            deal=self.deal, tx_type='COLLECTION', status='SUCCESS',
            amount='1000.00', payaza_ref='ref-1'
        )
        self.url = reverse('merchant-transactions')

    def test_list_transactions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentLinkTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username='seller1', password='pass1234', email='seller@test.com'
        )
        self.client.force_authenticate(user=self.seller)
        self.url = reverse('merchant-links')
        self.valid_data = {
            'item_description': 'Architecture Book',
            'amount': '5000.00',
            'delivery_days': 3,
            'buyer_email': 'buyer@test.com',
        }

    def test_create_payment_link(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('link_url', response.data)
        self.assertIn('trustpay.ng/pay/', response.data['link_url'])
        self.assertEqual(response.data['item_description'], 'Architecture Book')

    def test_list_payment_links(self):
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_link_url_format(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(
            response.data['link_url'],
            f"https://trustpay.ng/pay/{response.data['slug']}"
        )
