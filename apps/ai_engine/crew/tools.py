"""
CrewAI custom tools for the Nawwar electricity analysis crew.

Each tool wraps existing selectors and services to expose them
as CrewAI-compatible tools that agents can invoke during task execution.
"""
import json
import logging
from typing import Any

from crewai.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


class BillLookupTool(BaseTool):
    """Look up a consumer's bills by subscriber number."""

    name: str = "bill_lookup"
    description: str = (
        "Look up electricity bills for a consumer given their subscriber number. "
        "Returns the most recent bills with consumption, amounts, and billing periods. "
        "Input should be the subscriber number as a string."
    )

    def _run(self, subscriber_number: str) -> str:
        from apps.consumer.selectors import subscription_get_by_number, bill_list

        subscription = subscription_get_by_number(subscriber_number=subscriber_number)
        if not subscription:
            return json.dumps({"error": f"No subscription found for {subscriber_number}"})

        bills = list(bill_list(subscription=subscription, limit=6))
        if not bills:
            return json.dumps({"error": "No bills found for this subscription"})

        result = []
        for bill in bills:
            result.append({
                "billing_period": f"{bill.billing_period_start} to {bill.billing_period_end}",
                "total_kwh": float(bill.total_kwh),
                "peak_kwh": float(bill.peak_kwh),
                "off_peak_kwh": float(bill.off_peak_kwh),
                "total_amount_fils": bill.total_amount_fils,
                "total_amount_jod": round(bill.total_amount_fils / 1000, 3),
                "status": bill.status if hasattr(bill, 'status') else "unknown",
            })

        return json.dumps(result, default=str, ensure_ascii=False)


class TariffLookupTool(BaseTool):
    """Look up EMRC tariff tiers for a given sector."""

    name: str = "tariff_lookup"
    description: str = (
        "Look up the active EMRC electricity tariff tiers for a sector "
        "(residential, commercial, industrial). "
        "Input should be the sector name as a string."
    )

    def _run(self, sector: str) -> str:
        from apps.consumer.selectors import tariff_get_active, tariff_periods_list

        sector_upper = sector.strip().upper()
        if sector_upper not in ("RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL"):
            sector_upper = "RESIDENTIAL"

        tiers = list(tariff_get_active(sector=sector_upper))
        periods = list(tariff_periods_list())

        tier_data = []
        for tier in tiers:
            tier_data.append({
                "tier_number": tier.tier_number,
                "min_kwh": tier.min_kwh,
                "max_kwh": tier.max_kwh,
                "rate_fils": tier.rate_fils,
                "rate_jod": round(tier.rate_fils / 1000, 3),
            })

        period_data = []
        for period in periods:
            period_data.append({
                "name": period.name if hasattr(period, 'name') else str(period),
                "start_hour": period.start_hour,
                "end_hour": period.end_hour,
                "is_peak": period.is_peak,
                "multiplier": float(period.multiplier),
            })

        result = {
            "sector": sector_upper,
            "tiers": tier_data,
            "time_of_use_periods": period_data,
        }

        return json.dumps(result, default=str, ensure_ascii=False)


class SensorDataTool(BaseTool):
    """Retrieve sensor readings from power plant turbines."""

    name: str = "sensor_data"
    description: str = (
        "Retrieve recent sensor readings for a power plant turbine. "
        "Input should be a JSON string with 'turbine_id' (int) and "
        "optionally 'hours' (int, default 24)."
    )

    def _run(self, input_str: str) -> str:
        from apps.operations.selectors import sensor_readings_latest

        try:
            params = json.loads(input_str)
        except (json.JSONDecodeError, TypeError):
            params = {"turbine_id": input_str}

        turbine_id = params.get("turbine_id")
        hours = params.get("hours", 24)

        if not turbine_id:
            return json.dumps({"error": "turbine_id is required"})

        try:
            turbine_id = int(turbine_id)
        except (ValueError, TypeError):
            return json.dumps({"error": "turbine_id must be an integer"})

        readings = list(sensor_readings_latest(turbine_id=turbine_id, hours=int(hours))[:20])

        if not readings:
            return json.dumps({"message": "No sensor readings found for this turbine"})

        result = []
        for r in readings:
            result.append({
                "timestamp": str(r.timestamp),
                "sensor_type": r.sensor_type if hasattr(r, 'sensor_type') else "unknown",
                "value": float(r.value) if hasattr(r, 'value') else 0,
                "unit": r.unit if hasattr(r, 'unit') else "",
            })

        return json.dumps(result, default=str, ensure_ascii=False)


class ConsumptionAnalysisTool(BaseTool):
    """Analyze consumption patterns and calculate potential savings."""

    name: str = "consumption_analysis"
    description: str = (
        "Analyze a consumer's electricity consumption patterns and calculate "
        "potential savings. Input should be the subscriber number as a string."
    )

    def _run(self, subscriber_number: str) -> str:
        from apps.consumer.selectors import subscription_get_by_number
        from apps.ai_engine.services.optimizer_service import SavingsOptimizer

        subscription = subscription_get_by_number(subscriber_number=subscriber_number)
        if not subscription:
            return json.dumps({"error": f"No subscription found for {subscriber_number}"})

        optimizer = SavingsOptimizer()
        profile = optimizer.analyze_consumption(subscription_id=subscription.id)
        savings = optimizer.calculate_savings(consumption_profile=profile)

        result = {
            "consumption_profile": profile,
            "savings": savings,
        }

        return json.dumps(result, default=str, ensure_ascii=False)


class MaintenancePredictionTool(BaseTool):
    """Check active maintenance predictions for a plant."""

    name: str = "maintenance_predictions"
    description: str = (
        "Retrieve active (unacknowledged) maintenance predictions for a power plant. "
        "Input should be the plant code as a string, or 'all' for all plants."
    )

    def _run(self, plant_code: str) -> str:
        from apps.operations.selectors import maintenance_predictions_active

        code = plant_code.strip() if plant_code and plant_code.strip().lower() != "all" else None
        predictions = list(maintenance_predictions_active(plant_code=code)[:10])

        if not predictions:
            return json.dumps({"message": "No active maintenance predictions"})

        result = []
        for pred in predictions:
            result.append({
                "id": pred.id,
                "turbine": str(pred.turbine),
                "plant": pred.turbine.plant.code if pred.turbine and pred.turbine.plant else "unknown",
                "prediction_type": pred.prediction_type if hasattr(pred, 'prediction_type') else "unknown",
                "severity": pred.severity if hasattr(pred, 'severity') else "unknown",
                "predicted_date": str(pred.predicted_date) if hasattr(pred, 'predicted_date') else "",
                "description": pred.description if hasattr(pred, 'description') else "",
                "confidence": float(pred.confidence) if hasattr(pred, 'confidence') else 0,
            })

        return json.dumps(result, default=str, ensure_ascii=False)


class EmissionsLookupTool(BaseTool):
    """Look up emissions records for a power plant."""

    name: str = "emissions_lookup"
    description: str = (
        "Retrieve recent emissions records for a power plant. "
        "Input should be a JSON string with 'plant_code' (str) and "
        "optionally 'hours' (int, default 24)."
    )

    def _run(self, input_str: str) -> str:
        from apps.operations.selectors import emissions_latest

        try:
            params = json.loads(input_str)
        except (json.JSONDecodeError, TypeError):
            params = {"plant_code": input_str}

        plant_code = params.get("plant_code", "").strip()
        hours = params.get("hours", 24)

        if not plant_code:
            return json.dumps({"error": "plant_code is required"})

        records = list(emissions_latest(plant_code=plant_code, hours=int(hours))[:20])

        if not records:
            return json.dumps({"message": "No emissions records found"})

        result = []
        for rec in records:
            result.append({
                "timestamp": str(rec.timestamp),
                "co2_tons": float(rec.co2_tons) if hasattr(rec, 'co2_tons') else 0,
                "nox_kg": float(rec.nox_kg) if hasattr(rec, 'nox_kg') else 0,
                "so2_kg": float(rec.so2_kg) if hasattr(rec, 'so2_kg') else 0,
            })

        return json.dumps(result, default=str, ensure_ascii=False)


class DemandForecastTool(BaseTool):
    """Retrieve upcoming demand forecasts."""

    name: str = "demand_forecast"
    description: str = (
        "Retrieve upcoming electricity demand forecasts. "
        "Input should be the number of hours to forecast (int, default 24)."
    )

    def _run(self, hours: str = "24") -> str:
        from apps.operations.selectors import demand_forecast_upcoming

        try:
            h = int(hours)
        except (ValueError, TypeError):
            h = 24

        forecasts = list(demand_forecast_upcoming(hours=h)[:48])

        if not forecasts:
            return json.dumps({"message": "No demand forecasts available"})

        result = []
        for f in forecasts:
            result.append({
                "forecast_hour": str(f.forecast_hour),
                "predicted_mw": float(f.predicted_mw) if hasattr(f, 'predicted_mw') else 0,
                "confidence": float(f.confidence) if hasattr(f, 'confidence') else 0,
            })

        return json.dumps(result, default=str, ensure_ascii=False)


class WeatherTool(BaseTool):
    """Get current weather data for Amman, Jordan."""

    name: str = "weather_data"
    description: str = (
        "Get current weather data for Amman, Jordan. "
        "Useful for correlating energy demand with temperature. "
        "No input required — just pass an empty string."
    )

    def _run(self, _input: str = "") -> str:
        # Mock weather data for Jordan — in production this would call a weather API
        import random
        from datetime import datetime

        month = datetime.now().month
        # Seasonal temperature ranges for Amman
        if month in (6, 7, 8):  # Summer
            temp = random.randint(30, 42)
            humidity = random.randint(15, 35)
            condition = "sunny"
        elif month in (12, 1, 2):  # Winter
            temp = random.randint(3, 14)
            humidity = random.randint(55, 80)
            condition = random.choice(["cloudy", "rainy", "partly_cloudy"])
        else:  # Spring/Autumn
            temp = random.randint(15, 28)
            humidity = random.randint(30, 55)
            condition = random.choice(["sunny", "partly_cloudy"])

        result = {
            "location": "Amman, Jordan",
            "temperature_c": temp,
            "humidity_percent": humidity,
            "condition": condition,
            "wind_speed_kmh": random.randint(5, 30),
            "note": "Higher temperatures correlate with increased AC usage and electricity demand.",
        }

        return json.dumps(result, ensure_ascii=False)
