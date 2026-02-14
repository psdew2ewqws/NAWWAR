"""
SensorReading model - Time-series sensor data from turbines.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class SensorReading(TimeStampedModel):
    """A single sensor reading from a turbine."""

    class ReadingType(models.TextChoices):
        VIBRATION = 'vibration', 'Vibration (mm/s)'
        TEMPERATURE = 'temperature', 'Temperature (°C)'
        PRESSURE = 'pressure', 'Pressure (bar)'
        RPM = 'rpm', 'RPM'
        EXHAUST_TEMP = 'exhaust_temp', 'Exhaust Temperature (°C)'

    turbine = models.ForeignKey(
        'operations.Turbine',
        on_delete=models.CASCADE,
        related_name='sensor_readings',
    )
    timestamp = models.DateTimeField(db_index=True)
    reading_type = models.CharField(max_length=20, choices=ReadingType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=20)
    is_anomaly = models.BooleanField(default=False)
    anomaly_score = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = 'Sensor Reading'
        verbose_name_plural = 'Sensor Readings'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['turbine', 'reading_type', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.turbine} - {self.reading_type} @ {self.timestamp}'
