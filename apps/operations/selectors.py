"""
Operations selectors - Query logic for retrieving operations data.

Following the Django service/selector pattern: selectors contain
read-only query logic, services contain write/mutation logic.
"""
from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.operations.models import (
    Plant,
    Turbine,
    SensorReading,
    MaintenancePrediction,
    EmissionsRecord,
    HeatRateRecord,
    DemandForecast,
)


def plant_list(*, is_active: bool = True) -> QuerySet:
    """Return all active plants."""
    return Plant.objects.filter(is_active=is_active)


def plant_get_by_code(*, code: str) -> Plant | None:
    """Return a single plant by its code, or None."""
    try:
        return Plant.objects.get(code=code)
    except Plant.DoesNotExist:
        return None


def turbine_list(*, plant_code: str) -> QuerySet:
    """Return all turbines for a given plant."""
    return Turbine.objects.filter(
        plant__code=plant_code,
    ).select_related('plant')


def sensor_readings_latest(*, turbine_id: int, hours: int = 24) -> QuerySet:
    """Return sensor readings for a turbine within the last N hours."""
    cutoff = timezone.now() - timedelta(hours=hours)
    return SensorReading.objects.filter(
        turbine_id=turbine_id,
        timestamp__gte=cutoff,
    ).order_by('-timestamp')


def maintenance_predictions_active(*, plant_code: str | None = None) -> QuerySet:
    """Return active (unacknowledged) maintenance predictions."""
    qs = MaintenancePrediction.objects.filter(
        is_acknowledged=False,
    ).select_related('turbine', 'turbine__plant')

    if plant_code:
        qs = qs.filter(turbine__plant__code=plant_code)

    return qs


def emissions_latest(*, plant_code: str, hours: int = 24) -> QuerySet:
    """Return emissions records for a plant within the last N hours."""
    cutoff = timezone.now() - timedelta(hours=hours)
    return EmissionsRecord.objects.filter(
        plant__code=plant_code,
        timestamp__gte=cutoff,
    ).select_related('plant').order_by('-timestamp')


def demand_forecast_upcoming(*, hours: int = 24) -> QuerySet:
    """Return demand forecasts for the next N hours."""
    now = timezone.now()
    future = now + timedelta(hours=hours)
    return DemandForecast.objects.filter(
        forecast_hour__gte=now,
        forecast_hour__lte=future,
    ).order_by('forecast_hour')


def heat_rate_history(*, plant_code: str, days: int = 7) -> QuerySet:
    """Return heat rate records for a plant over the last N days."""
    cutoff = timezone.now() - timedelta(days=days)
    return HeatRateRecord.objects.filter(
        plant__code=plant_code,
        timestamp__gte=cutoff,
    ).select_related('plant').order_by('-timestamp')
