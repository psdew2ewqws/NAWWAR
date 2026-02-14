"""
EmissionsRecord model - Environmental emissions data per plant.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class EmissionsRecord(TimeStampedModel):
    """Emissions data for a power plant at a point in time."""

    plant = models.ForeignKey(
        'operations.Plant',
        on_delete=models.CASCADE,
        related_name='emissions_records',
    )
    timestamp = models.DateTimeField(db_index=True)
    nox_ppm = models.DecimalField(max_digits=8, decimal_places=2, help_text='NOx in ppm.')
    co2_tonnes = models.DecimalField(max_digits=10, decimal_places=2, help_text='CO2 in tonnes.')
    sox_ppm = models.DecimalField(max_digits=8, decimal_places=2, help_text='SOx in ppm.')
    nox_limit = models.DecimalField(max_digits=8, decimal_places=2, default=200)
    co2_limit = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    sox_limit = models.DecimalField(max_digits=8, decimal_places=2, default=150)
    is_compliant = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Emissions Record'
        verbose_name_plural = 'Emissions Records'
        ordering = ['-timestamp']

    def __str__(self):
        status = 'Compliant' if self.is_compliant else 'EXCEEDS LIMITS'
        return f'{self.plant.code} - {self.timestamp} [{status}]'
