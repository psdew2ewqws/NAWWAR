"""
DemandForecast model - Grid demand forecasting data.
"""
from django.db import models

from apps.core.models import TimeStampedModel


class DemandForecast(TimeStampedModel):
    """A demand forecast record for grid planning."""

    timestamp = models.DateTimeField(
        help_text='When the forecast was generated.',
        db_index=True,
    )
    forecast_hour = models.DateTimeField(help_text='The hour being forecasted.')
    predicted_mw = models.DecimalField(max_digits=10, decimal_places=2)
    actual_mw = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confidence_lower = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_upper = models.DecimalField(max_digits=10, decimal_places=2)
    model_version = models.CharField(max_length=50, default='v1.0')

    class Meta:
        verbose_name = 'Demand Forecast'
        verbose_name_plural = 'Demand Forecasts'
        ordering = ['-forecast_hour']

    def __str__(self):
        return f'Forecast {self.predicted_mw} MW for {self.forecast_hour}'
