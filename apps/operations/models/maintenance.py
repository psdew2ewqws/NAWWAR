"""
MaintenancePrediction model - AI-generated maintenance predictions.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class MaintenancePrediction(TimeStampedModel):
    """A predictive maintenance alert for a turbine."""

    class PredictionType(models.TextChoices):
        BEARING = 'bearing', 'Bearing Failure'
        BLADE = 'blade', 'Blade Degradation'
        SEAL = 'seal', 'Seal Leak'
        GEARBOX = 'gearbox', 'Gearbox Failure'
        OTHER = 'other', 'Other'

    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    turbine = models.ForeignKey(
        'operations.Turbine',
        on_delete=models.CASCADE,
        related_name='maintenance_predictions',
    )
    prediction_type = models.CharField(max_length=20, choices=PredictionType.choices)
    confidence = models.FloatField(help_text='Confidence score 0.0 to 1.0.')
    predicted_failure_date = models.DateField()
    severity = models.CharField(max_length=10, choices=Severity.choices)
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    recommended_action = models.TextField(blank=True)
    recommended_action_ar = models.TextField(blank=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_predictions',
    )

    class Meta:
        verbose_name = 'Maintenance Prediction'
        verbose_name_plural = 'Maintenance Predictions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.turbine} - {self.prediction_type} ({self.severity})'
