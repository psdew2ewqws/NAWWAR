"""
Operations API serializers.
"""
from rest_framework import serializers

from apps.operations.models import (
    Plant,
    Turbine,
    SensorReading,
    MaintenancePrediction,
    EmissionsRecord,
    HeatRateRecord,
    DemandForecast,
)


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = [
            'id', 'code', 'name', 'name_ar', 'plant_type', 'fuel_type',
            'capacity_mw', 'commissioned_year', 'latitude', 'longitude',
            'status', 'current_load_mw', 'efficiency_percent', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TurbineSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source='plant.code', read_only=True)

    class Meta:
        model = Turbine
        fields = [
            'id', 'plant', 'plant_code', 'turbine_id', 'name', 'capacity_mw',
            'status', 'hours_since_maintenance', 'next_maintenance_date',
            'last_maintenance_date', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SensorReadingSerializer(serializers.ModelSerializer):
    turbine_label = serializers.CharField(source='turbine.__str__', read_only=True)

    class Meta:
        model = SensorReading
        fields = [
            'id', 'turbine', 'turbine_label', 'timestamp', 'reading_type',
            'value', 'unit', 'is_anomaly', 'anomaly_score',
        ]
        read_only_fields = ['id']


class MaintenancePredictionSerializer(serializers.ModelSerializer):
    turbine_label = serializers.CharField(source='turbine.__str__', read_only=True)

    class Meta:
        model = MaintenancePrediction
        fields = [
            'id', 'turbine', 'turbine_label', 'prediction_type', 'confidence',
            'predicted_failure_date', 'severity', 'description', 'description_ar',
            'recommended_action', 'recommended_action_ar', 'is_acknowledged',
            'acknowledged_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmissionsRecordSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source='plant.code', read_only=True)

    class Meta:
        model = EmissionsRecord
        fields = [
            'id', 'plant', 'plant_code', 'timestamp', 'nox_ppm', 'co2_tonnes',
            'sox_ppm', 'nox_limit', 'co2_limit', 'sox_limit', 'is_compliant',
        ]
        read_only_fields = ['id']


class HeatRateRecordSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source='plant.code', read_only=True)

    class Meta:
        model = HeatRateRecord
        fields = [
            'id', 'plant', 'plant_code', 'timestamp', 'heat_rate_btu_kwh',
            'fuel_consumption_kg', 'power_output_mw', 'ambient_temp_c',
        ]
        read_only_fields = ['id']


class DemandForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandForecast
        fields = [
            'id', 'timestamp', 'forecast_hour', 'predicted_mw', 'actual_mw',
            'confidence_lower', 'confidence_upper', 'model_version',
        ]
        read_only_fields = ['id']
