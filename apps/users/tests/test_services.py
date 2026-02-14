"""
Tests for user services.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.users import services
from apps.core.exceptions import ValidationError

User = get_user_model()


class UserCreateServiceTest(TestCase):
    """Tests for user_create service."""

    def test_user_create_success(self):
        """Test creating a user successfully."""
        user = services.user_create(
            email='test@example.com',
            password='securepassword123',
            first_name='John',
            last_name='Doe'
        )

        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertTrue(user.check_password('securepassword123'))

    def test_user_create_duplicate_email_fails(self):
        """Test that creating a user with duplicate email fails."""
        services.user_create(
            email='test@example.com',
            password='securepassword123'
        )

        with self.assertRaises(ValidationError):
            services.user_create(
                email='test@example.com',
                password='anotherpassword123'
            )


class UserUpdateServiceTest(TestCase):
    """Tests for user_update service."""

    def setUp(self):
        self.user = services.user_create(
            email='test@example.com',
            password='securepassword123'
        )

    def test_user_update_success(self):
        """Test updating a user successfully."""
        updated_user = services.user_update(
            user=self.user,
            data={'first_name': 'Jane', 'last_name': 'Smith'}
        )

        self.assertEqual(updated_user.first_name, 'Jane')
        self.assertEqual(updated_user.last_name, 'Smith')
