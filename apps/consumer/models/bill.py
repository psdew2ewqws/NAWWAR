"""
Bill and BillLineItem models - Electricity billing data.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Bill(TimeStampedModel):
    """An electricity bill for a subscription."""

    subscription = models.ForeignKey(
        'consumer.Subscription',
        on_delete=models.CASCADE,
        related_name='bills',
    )
    billing_period_start = models.DateField()
    billing_period_end = models.DateField()
    total_amount_fils = models.PositiveIntegerField(default=0)
    total_kwh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peak_kwh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    off_peak_kwh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_reading = models.PositiveIntegerField(default=0)
    current_reading = models.PositiveIntegerField(default=0)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    scanned_image = models.ImageField(upload_to='bills/scans/', blank=True, null=True)
    raw_ocr_data = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'
        ordering = ['-billing_period_end']

    def __str__(self):
        return f'Bill {self.id} - {self.subscription.subscriber_number} ({self.billing_period_end})'


class BillLineItem(TimeStampedModel):
    """A line item on a bill (tariff breakdown, taxes, fees)."""

    bill = models.ForeignKey(
        'consumer.Bill',
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    description = models.CharField(max_length=255)
    description_ar = models.CharField(max_length=255, blank=True)
    amount_fils = models.IntegerField(default=0)
    kwh = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tariff_tier = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Bill Line Item'
        verbose_name_plural = 'Bill Line Items'
        ordering = ['id']

    def __str__(self):
        return f'{self.description} - {self.amount_fils} fils'
