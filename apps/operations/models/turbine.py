"""
Turbine model - Represents a turbine within a plant.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Turbine(TimeStampedModel):
    """A turbine unit within a power plant."""

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
        TRIP = 'trip', 'Tripped'

    plant = models.ForeignKey(
        'operations.Plant',
        on_delete=models.CASCADE,
        related_name='turbines',
    )
    turbine_id = models.CharField(max_length=10, help_text='Turbine identifier, e.g. A1.')
    name = models.CharField(max_length=100, blank=True)
    capacity_mw = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ONLINE,
    )
    hours_since_maintenance = models.PositiveIntegerField(default=0)
    next_maintenance_date = models.DateField(null=True, blank=True)
    last_maintenance_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Turbine'
        verbose_name_plural = 'Turbines'
        ordering = ['plant', 'turbine_id']
        unique_together = ['plant', 'turbine_id']

    def __str__(self):
        return f'{self.plant.code}-{self.turbine_id}'
