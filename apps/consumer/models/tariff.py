"""
Tariff models - Electricity tariff tiers and time-of-use periods.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class TariffTier(TimeStampedModel):
    """A tariff tier defining price per kWh for a consumption range."""

    class Sector(models.TextChoices):
        RESIDENTIAL = 'residential', 'Residential'
        COMMERCIAL = 'commercial', 'Commercial'
        INDUSTRIAL = 'industrial', 'Industrial'

    sector = models.CharField(max_length=20, choices=Sector.choices)
    tier_number = models.PositiveSmallIntegerField()
    min_kwh = models.PositiveIntegerField()
    max_kwh = models.PositiveIntegerField(help_text='Use 999999 for unlimited.')
    rate_fils = models.PositiveIntegerField(help_text='Rate in fils per kWh.')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tariff Tier'
        verbose_name_plural = 'Tariff Tiers'
        ordering = ['sector', 'tier_number']
        unique_together = ['sector', 'tier_number']

    def __str__(self):
        return f'{self.get_sector_display()} Tier {self.tier_number} ({self.rate_fils} fils/kWh)'


class TariffPeriod(TimeStampedModel):
    """A time-of-use period (peak / off-peak)."""

    name = models.CharField(max_length=50)
    name_ar = models.CharField(max_length=50, blank=True)
    start_hour = models.PositiveSmallIntegerField(help_text='Hour of day (0-23).')
    end_hour = models.PositiveSmallIntegerField(help_text='Hour of day (0-23).')
    multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.00,
        help_text='Rate multiplier for this period.',
    )
    is_peak = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Tariff Period'
        verbose_name_plural = 'Tariff Periods'
        ordering = ['start_hour']

    def __str__(self):
        return f'{self.name} ({self.start_hour}:00 - {self.end_hour}:00)'
