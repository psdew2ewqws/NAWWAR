"""
Tests for user selectors.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.users import selectors, services

User = get_user_model()


class UserSelectorsTest(TestCase):
    """Tests for user selectors."""

    def setUp(self):
        self.user1 = services.user_create(
            email='user1@example.com',
            password='password123'
        )
        self.user2 = services.user_create(
            email='user2@example.com',
            password='password123'
        )
        services.user_verify(user=self.user1)

    def test_user_list_returns_all_active(self):
        """Test user_list returns all active users."""
        users = selectors.user_list()
        self.assertEqual(users.count(), 2)

    def test_user_list_filters_verified(self):
        """Test user_list filters by verified status."""
        verified = selectors.user_list(is_verified=True)
        unverified = selectors.user_list(is_verified=False)

        self.assertEqual(verified.count(), 1)
        self.assertEqual(unverified.count(), 1)

    def test_user_get_by_email(self):
        """Test user_get_by_email returns correct user."""
        user = selectors.user_get_by_email(email='user1@example.com')
        self.assertEqual(user, self.user1)

    def test_user_get_by_email_not_found(self):
        """Test user_get_by_email returns None for non-existent email."""
        user = selectors.user_get_by_email(email='nonexistent@example.com')
        self.assertIsNone(user)
