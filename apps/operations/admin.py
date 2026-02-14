"""
Operations admin - Register all operations models.
"""
from django.contrib import admin

from .models import (
    Plant,
    Turbine,
    SensorReading,
    MaintenancePrediction,
    EmissionsRecord,
    HeatRateRecord,
    DemandForecast,
)


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'plant_type', 'capacity_mw', 'status', 'current_load_mw', 'is_active']
    list_filter = ['plant_type', 'status', 'is_active']
    search_fields = ['code', 'name', 'name_ar']


@admin.register(Turbine)
class TurbineAdmin(admin.ModelAdmin):
    list_display = ['turbine_id', 'plant', 'capacity_mw', 'status', 'hours_since_maintenance']
    list_filter = ['status', 'plant']
    search_fields = ['turbine_id', 'name', 'plant__code']


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ['turbine', 'reading_type', 'value', 'unit', 'timestamp', 'is_anomaly']
    list_filter = ['reading_type', 'is_anomaly', 'turbine__plant']
    search_fields = ['turbine__turbine_id', 'turbine__plant__code']
    date_hierarchy = 'timestamp'


@admin.register(MaintenancePrediction)
class MaintenancePredictionAdmin(admin.ModelAdmin):
    list_display = [
        'turbine', 'prediction_type', 'severity', 'confidence',
        'predicted_failure_date', 'is_acknowledged',
    ]
    list_filter = ['prediction_type', 'severity', 'is_acknowledged']
    search_fields = ['turbine__turbine_id', 'description']


@admin.register(EmissionsRecord)
class EmissionsRecordAdmin(admin.ModelAdmin):
    list_display = ['plant', 'timestamp', 'nox_ppm', 'co2_tonnes', 'sox_ppm', 'is_compliant']
    list_filter = ['is_compliant', 'plant']
    date_hierarchy = 'timestamp'


@admin.register(HeatRateRecord)
class HeatRateRecordAdmin(admin.ModelAdmin):
    list_display = ['plant', 'timestamp', 'heat_rate_btu_kwh', 'fuel_consumption_kg', 'power_output_mw']
    list_filter = ['plant']
    date_hierarchy = 'timestamp'


@admin.register(DemandForecast)
class DemandForecastAdmin(admin.ModelAdmin):
    list_display = ['forecast_hour', 'predicted_mw', 'actual_mw', 'model_version', 'timestamp']
    list_filter = ['model_version']
    date_hierarchy = 'forecast_hour'
