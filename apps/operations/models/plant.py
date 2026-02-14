"""
Plant model - Represents a CEGCO power generation plant.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class Plant(TimeStampedModel):
    """A CEGCO power generation plant."""

    class PlantType(models.TextChoices):
        STEAM = 'steam', 'Steam Turbine'
        GAS = 'gas', 'Gas Turbine'
        CCGT = 'ccgt', 'Combined Cycle Gas Turbine'

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        MAINTENANCE = 'maintenance', 'Under Maintenance'
        DERATED = 'derated', 'Derated'

    code = models.CharField(max_length=20, unique=True, help_text='Plant code, e.g. AQABA.')
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True)
    plant_type = models.CharField(max_length=10, choices=PlantType.choices)
    fuel_type = models.CharField(max_length=100, blank=True)
    capacity_mw = models.DecimalField(max_digits=8, decimal_places=2)
    commissioned_year = models.PositiveIntegerField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ONLINE,
    )
    current_load_mw = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    efficiency_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plant'
        verbose_name_plural = 'Plants'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'
