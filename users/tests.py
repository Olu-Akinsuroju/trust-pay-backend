from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class UserRegistrationTests(APITestCase):
    """Tests for user registration endpoint."""

    def setUp(self):
        self.register_url = '/api/auth/register/'

    def test_register_with_valid_data_returns_201(self):
        """Register with valid data returns 201."""
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'email': 'test@example.com',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_with_duplicate_username_returns_400(self):
        """Register with duplicate username returns 400."""
        User.objects.create_user(username='duplicate', password='pass123')
        data = {
            'username': 'duplicate',
            'password': 'testpass123',
            'email': 'other@example.com',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_with_missing_password_returns_400(self):
        """Register with missing password returns 400."""
        data = {
            'username': 'nopassuser',
            'email': 'nopass@example.com',
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTests(APITestCase):
    """Tests for user login (JWT token obtain) endpoint."""

    def setUp(self):
        self.login_url = '/api/auth/login/'
        self.user = User.objects.create_user(
            username='loginuser',
            password='securepass123',
            email='login@example.com',
        )

    def test_login_with_correct_credentials_returns_tokens(self):
        """Login with correct credentials returns access/refresh tokens."""
        data = {
            'username': 'loginuser',
            'password': 'securepass123',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_wrong_password_returns_401(self):
        """Login with wrong password returns 401."""
        data = {
            'username': 'loginuser',
            'password': 'wrongpassword',
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTests(APITestCase):
    """Tests for JWT token refresh endpoint."""

    def setUp(self):
        self.refresh_url = '/api/auth/refresh/'
        self.login_url = '/api/auth/login/'
        self.user = User.objects.create_user(
            username='refreshuser',
            password='refreshpass123',
            email='refresh@example.com',
        )
        # Get a valid refresh token
        login_response = self.client.post(self.login_url, {
            'username': 'refreshuser',
            'password': 'refreshpass123',
        }, format='json')
        self.refresh_token = login_response.data['refresh']

    def test_token_refresh_works_with_valid_refresh_token(self):
        """Token refresh works with valid refresh token."""
        data = {'refresh': self.refresh_token}
        response = self.client.post(self.refresh_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
