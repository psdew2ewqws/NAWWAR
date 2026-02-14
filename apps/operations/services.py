"""
Operations services - Business logic for operations domain.

Following the Django service/selector pattern: services contain
write/mutation logic and orchestrate ML pipelines.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.operations.ml.anomaly_detector import AnomalyDetector
from apps.operations.ml.demand_forecaster import DemandForecaster
from apps.operations.models import (
    Plant,
    Turbine,
    MaintenancePrediction,
    DemandForecast,
)
from apps.operations import selectors

logger = logging.getLogger(__name__)


def run_anomaly_detection(*, plant_code: str | None = None) -> list[dict]:
    """
    Run anomaly detection on turbines and create maintenance predictions.

    Args:
        plant_code: Optional plant code to limit detection to one plant.

    Returns:
        List of prediction dicts for turbines with detected risks.
    """
    if plant_code:
        turbines = Turbine.objects.filter(plant__code=plant_code).select_related('plant')
    else:
        turbines = Turbine.objects.filter(
            plant__is_active=True,
        ).select_related('plant')

    detector = AnomalyDetector()
    predictions = []

    for turbine in turbines:
        try:
            result = detector.predict_failure(turbine_id=turbine.pk)

            if result['has_risk']:
                prediction = _create_or_update_prediction(
                    turbine=turbine,
                    result=result,
                )
                predictions.append({
                    'turbine': str(turbine),
                    'turbine_id': turbine.pk,
                    'plant_code': turbine.plant.code,
                    **result,
                })
                logger.info(
                    'Anomaly detected for %s: %s (%s)',
                    turbine, result['failure_type'], result['severity'],
                )
            else:
                predictions.append({
                    'turbine': str(turbine),
                    'turbine_id': turbine.pk,
                    'plant_code': turbine.plant.code,
                    **result,
                })
        except Exception:
            logger.exception('Error running anomaly detection for turbine %s', turbine)

    return predictions


@transaction.atomic
def _create_or_update_prediction(*, turbine: Turbine, result: dict) -> MaintenancePrediction:
    """Create or update a maintenance prediction for a turbine."""
    from datetime import date

    failure_date_str = result.get('predicted_failure_date')
    if failure_date_str:
        predicted_date = date.fromisoformat(failure_date_str)
    else:
        predicted_date = (timezone.now() + timedelta(days=30)).date()

    prediction, created = MaintenancePrediction.objects.update_or_create(
        turbine=turbine,
        is_acknowledged=False,
        prediction_type=result.get('failure_type', 'other'),
        defaults={
            'confidence': result.get('confidence', 0.5),
            'predicted_failure_date': predicted_date,
            'severity': result.get('severity', 'medium'),
            'description': result.get('description', ''),
            'recommended_action': result.get('recommended_action', ''),
        },
    )
    return prediction


def generate_demand_forecast(*, hours_ahead: int = 24) -> list[dict]:
    """
    Generate demand forecast and store results.

    Args:
        hours_ahead: Number of hours to forecast.

    Returns:
        List of forecast dicts.
    """
    forecaster = DemandForecaster()
    forecasts = forecaster.generate_forecast(hours_ahead=hours_ahead)

    now = timezone.now()

    with transaction.atomic():
        for fc in forecasts:
            from datetime import datetime
            forecast_hour = datetime.fromisoformat(fc['timestamp'])
            if timezone.is_naive(forecast_hour):
                forecast_hour = timezone.make_aware(forecast_hour)

            DemandForecast.objects.update_or_create(
                forecast_hour=forecast_hour,
                model_version='v2.0-sklearn',
                defaults={
                    'timestamp': now,
                    'predicted_mw': fc['predicted_mw'],
                    'confidence_lower': fc['confidence_lower'],
                    'confidence_upper': fc['confidence_upper'],
                },
            )

    return forecasts


def calculate_emissions_status(*, plant_code: str) -> dict:
    """
    Calculate current emissions compliance status for a plant.

    Args:
        plant_code: The plant code to check.

    Returns:
        Dict with NOx, CO2, SOx status and overall compliance.
    """
    plant = selectors.plant_get_by_code(code=plant_code)
    if not plant:
        return {'error': f'Plant {plant_code} not found.'}

    latest_emissions = selectors.emissions_latest(plant_code=plant_code, hours=24)

    if not latest_emissions.exists():
        return {
            'plant': plant_code,
            'nox_status': 'no_data',
            'co2_status': 'no_data',
            'sox_status': 'no_data',
            'overall_compliant': True,
            'message': 'No recent emissions data available.',
        }

    latest = latest_emissions.first()

    nox_ok = latest.nox_ppm <= latest.nox_limit
    co2_ok = latest.co2_tonnes <= latest.co2_limit
    sox_ok = latest.sox_ppm <= latest.sox_limit

    # Count violations in last 24h
    violations = latest_emissions.filter(is_compliant=False).count()
    total = latest_emissions.count()

    return {
        'plant': plant_code,
        'nox_status': 'compliant' if nox_ok else 'exceeds_limit',
        'nox_ppm': float(latest.nox_ppm),
        'nox_limit': float(latest.nox_limit),
        'co2_status': 'compliant' if co2_ok else 'exceeds_limit',
        'co2_tonnes': float(latest.co2_tonnes),
        'co2_limit': float(latest.co2_limit),
        'sox_status': 'compliant' if sox_ok else 'exceeds_limit',
        'sox_ppm': float(latest.sox_ppm),
        'sox_limit': float(latest.sox_limit),
        'overall_compliant': nox_ok and co2_ok and sox_ok,
        'violations_24h': violations,
        'total_readings_24h': total,
    }


def get_plant_overview(*, plant_code: str) -> dict:
    """
    Get a comprehensive overview of a plant's status.

    Includes turbine status, active alerts, emissions compliance,
    and recent performance data.

    Args:
        plant_code: The plant code.

    Returns:
        Dict with comprehensive plant status.
    """
    plant = selectors.plant_get_by_code(code=plant_code)
    if not plant:
        return {'error': f'Plant {plant_code} not found.'}

    turbines = selectors.turbine_list(plant_code=plant_code)
    active_predictions = selectors.maintenance_predictions_active(plant_code=plant_code)
    emissions = calculate_emissions_status(plant_code=plant_code)
    heat_rates = selectors.heat_rate_history(plant_code=plant_code, days=1)

    turbine_summaries = []
    for t in turbines:
        turbine_summaries.append({
            'id': t.pk,
            'turbine_id': t.turbine_id,
            'name': t.name,
            'status': t.status,
            'capacity_mw': float(t.capacity_mw),
            'hours_since_maintenance': t.hours_since_maintenance,
        })

    alert_summaries = []
    for p in active_predictions[:10]:
        alert_summaries.append({
            'id': p.pk,
            'turbine': str(p.turbine),
            'type': p.prediction_type,
            'severity': p.severity,
            'confidence': p.confidence,
            'predicted_date': p.predicted_failure_date.isoformat() if p.predicted_failure_date else None,
            'description': p.description,
        })

    latest_heat_rate = None
    if heat_rates.exists():
        hr = heat_rates.first()
        latest_heat_rate = {
            'heat_rate_btu_kwh': float(hr.heat_rate_btu_kwh),
            'power_output_mw': float(hr.power_output_mw),
            'fuel_consumption_kg': float(hr.fuel_consumption_kg),
        }

    return {
        'plant': {
            'code': plant.code,
            'name': plant.name,
            'type': plant.plant_type,
            'status': plant.status,
            'capacity_mw': float(plant.capacity_mw),
            'current_load_mw': float(plant.current_load_mw),
            'efficiency_percent': float(plant.efficiency_percent),
        },
        'turbines': turbine_summaries,
        'active_alerts': alert_summaries,
        'alert_count': active_predictions.count(),
        'emissions': emissions,
        'latest_heat_rate': latest_heat_rate,
    }
