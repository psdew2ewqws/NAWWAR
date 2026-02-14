"""
User model - Custom user model with best practices.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """Custom User model with additional fields."""

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'.strip() or self.username
