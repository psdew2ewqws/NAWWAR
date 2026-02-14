"""
HeatRateRecord model - Thermal efficiency data per plant.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class HeatRateRecord(TimeStampedModel):
    """Heat rate and fuel consumption record for a power plant."""

    plant = models.ForeignKey(
        'operations.Plant',
        on_delete=models.CASCADE,
        related_name='heat_rate_records',
    )
    timestamp = models.DateTimeField(db_index=True)
    heat_rate_btu_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Heat rate in BTU/kWh.',
    )
    fuel_consumption_kg = models.DecimalField(max_digits=10, decimal_places=2)
    power_output_mw = models.DecimalField(max_digits=8, decimal_places=2)
    ambient_temp_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Heat Rate Record'
        verbose_name_plural = 'Heat Rate Records'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.plant.code} - {self.heat_rate_btu_kwh} BTU/kWh @ {self.timestamp}'
