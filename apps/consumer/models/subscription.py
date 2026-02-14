"""
Subscription model - Represents a JEPCO electricity subscription.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Subscription(TimeStampedModel):
    """A JEPCO electricity subscription linked to a consumer."""

    class SubscriptionType(models.TextChoices):
        RESIDENTIAL = 'residential', 'Residential'
        COMMERCIAL = 'commercial', 'Commercial'
        INDUSTRIAL = 'industrial', 'Industrial'

    subscriber_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    address_ar = models.TextField(blank=True)
    district = models.CharField(max_length=100, blank=True)
    meter_number = models.CharField(max_length=50, blank=True)
    subscription_type = models.CharField(
        max_length=20,
        choices=SubscriptionType.choices,
        default=SubscriptionType.RESIDENTIAL,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.subscriber_number} - {self.name}'
