"""
Complaint model - Customer complaints and service requests.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Complaint(TimeStampedModel):
    """A complaint or service request filed by a consumer."""

    class ComplaintType(models.TextChoices):
        OUTAGE = 'outage', 'Power Outage'
        BILLING = 'billing', 'Billing Issue'
        METER = 'meter', 'Meter Problem'
        VOLTAGE = 'voltage', 'Voltage Issue'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    subscription = models.ForeignKey(
        'consumer.Subscription',
        on_delete=models.CASCADE,
        related_name='complaints',
    )
    complaint_type = models.CharField(
        max_length=20,
        choices=ComplaintType.choices,
    )
    description = models.TextField()
    description_ar = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    jepco_reference = models.CharField(max_length=100, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Complaint'
        verbose_name_plural = 'Complaints'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_complaint_type_display()} - {self.subscription.subscriber_number}'
