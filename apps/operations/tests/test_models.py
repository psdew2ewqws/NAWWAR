"""
Tests for operations app models.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.operations.models import (
    Plant,
    Turbine,
    SensorReading,
    MaintenancePrediction,
    EmissionsRecord,
    DemandForecast,
    HeatRateRecord,
)


class PlantModelTest(TestCase):
    """Tests for the Plant model."""

    def setUp(self):
        self.plant = Plant.objects.create(
            code='AQABA',
            name='Aqaba Thermal Power Station',
            plant_type=Plant.PlantType.STEAM,
            capacity_mw=Decimal('656.00'),
        )

    def test_plant_creation(self):
        self.assertEqual(self.plant.code, 'AQABA')
        self.assertEqual(self.plant.name, 'Aqaba Thermal Power Station')
        self.assertEqual(self.plant.plant_type, 'steam')
        self.assertEqual(self.plant.capacity_mw, Decimal('656.00'))
        self.assertTrue(self.plant.is_active)

    def test_plant_str(self):
        self.assertEqual(str(self.plant), 'AQABA - Aqaba Thermal Power Station')

    def test_plant_default_status(self):
        self.assertEqual(self.plant.status, Plant.Status.ONLINE)

    def test_plant_default_load(self):
        self.assertEqual(self.plant.current_load_mw, Decimal('0'))

    def test_plant_code_unique(self):
        with self.assertRaises(Exception):
            Plant.objects.create(
                code='AQABA',
                name='Duplicate',
                plant_type=Plant.PlantType.GAS,
                capacity_mw=Decimal('100.00'),
            )

    def test_plant_type_choices(self):
        self.assertIn(('steam', 'Steam Turbine'), Plant.PlantType.choices)
        self.assertIn(('gas', 'Gas Turbine'), Plant.PlantType.choices)
        self.assertIn(('ccgt', 'Combined Cycle Gas Turbine'), Plant.PlantType.choices)

    def test_plant_status_choices(self):
        self.assertIn(('online', 'Online'), Plant.Status.choices)
        self.assertIn(('offline', 'Offline'), Plant.Status.choices)
        self.assertIn(('maintenance', 'Under Maintenance'), Plant.Status.choices)
        self.assertIn(('derated', 'Derated'), Plant.Status.choices)

    def test_plant_timestamps(self):
        self.assertIsNotNone(self.plant.created_at)
        self.assertIsNotNone(self.plant.updated_at)


class TurbineModelTest(TestCase):
    """Tests for the Turbine model."""

    def setUp(self):
        self.plant = Plant.objects.create(
            code='REHAB',
            name='Rehab Gas Power Station',
            plant_type=Plant.PlantType.GAS,
            capacity_mw=Decimal('357.00'),
        )
        self.turbine = Turbine.objects.create(
            plant=self.plant,
            turbine_id='A1',
            name='Gas Turbine A1',
            capacity_mw=Decimal('60.00'),
        )

    def test_turbine_creation(self):
        self.assertEqual(self.turbine.turbine_id, 'A1')
        self.assertEqual(self.turbine.plant, self.plant)
        self.assertEqual(self.turbine.capacity_mw, Decimal('60.00'))

    def test_turbine_str(self):
        self.assertEqual(str(self.turbine), 'REHAB-A1')

    def test_turbine_default_status(self):
        self.assertEqual(self.turbine.status, Turbine.Status.ONLINE)

    def test_turbine_plant_relationship(self):
        self.assertIn(self.turbine, self.plant.turbines.all())

    def test_turbine_unique_together(self):
        with self.assertRaises(Exception):
            Turbine.objects.create(
                plant=self.plant,
                turbine_id='A1',
                name='Duplicate',
                capacity_mw=Decimal('50.00'),
            )

    def test_turbine_hours_since_maintenance_default(self):
        self.assertEqual(self.turbine.hours_since_maintenance, 0)


class SensorReadingModelTest(TestCase):
    """Tests for the SensorReading model."""

    def setUp(self):
        self.plant = Plant.objects.create(
            code='SAMRA',
            name='Samra Power Plant',
            plant_type=Plant.PlantType.CCGT,
            capacity_mw=Decimal('900.00'),
        )
        self.turbine = Turbine.objects.create(
            plant=self.plant,
            turbine_id='GT1',
            capacity_mw=Decimal('150.00'),
        )
        self.reading = SensorReading.objects.create(
            turbine=self.turbine,
            timestamp=timezone.now(),
            reading_type=SensorReading.ReadingType.VIBRATION,
            value=Decimal('3.5000'),
            unit='mm/s',
        )

    def test_sensor_reading_creation(self):
        self.assertEqual(self.reading.turbine, self.turbine)
        self.assertEqual(self.reading.reading_type, 'vibration')
        self.assertEqual(self.reading.value, Decimal('3.5000'))
        self.assertEqual(self.reading.unit, 'mm/s')

    def test_sensor_reading_default_anomaly(self):
        self.assertFalse(self.reading.is_anomaly)

    def test_sensor_reading_with_anomaly(self):
        reading = SensorReading.objects.create(
            turbine=self.turbine,
            timestamp=timezone.now(),
            reading_type=SensorReading.ReadingType.TEMPERATURE,
            value=Decimal('850.0000'),
            unit='C',
            is_anomaly=True,
            anomaly_score=0.85,
        )
        self.assertTrue(reading.is_anomaly)
        self.assertEqual(reading.anomaly_score, 0.85)

    def test_sensor_reading_str(self):
        self.assertIn('SAMRA-GT1', str(self.reading))
        self.assertIn('vibration', str(self.reading))

    def test_reading_type_choices(self):
        self.assertIn(('vibration', 'Vibration (mm/s)'), SensorReading.ReadingType.choices)
        self.assertIn(('temperature', 'Temperature (°C)'), SensorReading.ReadingType.choices)
        self.assertIn(('pressure', 'Pressure (bar)'), SensorReading.ReadingType.choices)
        self.assertIn(('rpm', 'RPM'), SensorReading.ReadingType.choices)
        self.assertIn(('exhaust_temp', 'Exhaust Temperature (°C)'), SensorReading.ReadingType.choices)


class MaintenancePredictionModelTest(TestCase):
    """Tests for the MaintenancePrediction model."""

    def setUp(self):
        self.plant = Plant.objects.create(
            code='HUSSEIN',
            name='Hussein Thermal Power Station',
            plant_type=Plant.PlantType.STEAM,
            capacity_mw=Decimal('396.00'),
        )
        self.turbine = Turbine.objects.create(
            plant=self.plant,
            turbine_id='ST1',
            capacity_mw=Decimal('66.00'),
        )
        self.prediction = MaintenancePrediction.objects.create(
            turbine=self.turbine,
            prediction_type=MaintenancePrediction.PredictionType.BEARING,
            confidence=0.85,
            predicted_failure_date=date.today() + timedelta(days=7),
            severity=MaintenancePrediction.Severity.HIGH,
            description='High vibration trend detected.',
        )

    def test_prediction_creation(self):
        self.assertEqual(self.prediction.turbine, self.turbine)
        self.assertEqual(self.prediction.prediction_type, 'bearing')
        self.assertEqual(self.prediction.confidence, 0.85)
        self.assertEqual(self.prediction.severity, 'high')

    def test_prediction_str(self):
        self.assertEqual(str(self.prediction), 'HUSSEIN-ST1 - bearing (high)')

    def test_prediction_default_acknowledged(self):
        self.assertFalse(self.prediction.is_acknowledged)

    def test_severity_choices(self):
        self.assertIn(('low', 'Low'), MaintenancePrediction.Severity.choices)
        self.assertIn(('medium', 'Medium'), MaintenancePrediction.Severity.choices)
        self.assertIn(('high', 'High'), MaintenancePrediction.Severity.choices)
        self.assertIn(('critical', 'Critical'), MaintenancePrediction.Severity.choices)

    def test_prediction_type_choices(self):
        self.assertIn(('bearing', 'Bearing Failure'), MaintenancePrediction.PredictionType.choices)
        self.assertIn(('blade', 'Blade Degradation'), MaintenancePrediction.PredictionType.choices)
        self.assertIn(('seal', 'Seal Leak'), MaintenancePrediction.PredictionType.choices)
        self.assertIn(('gearbox', 'Gearbox Failure'), MaintenancePrediction.PredictionType.choices)


class EmissionsRecordModelTest(TestCase):
    """Tests for the EmissionsRecord model."""

    def setUp(self):
        self.plant = Plant.objects.create(
            code='RISHA',
            name='Risha Gas Power Station',
            plant_type=Plant.PlantType.GAS,
            capacity_mw=Decimal('150.00'),
        )
        self.compliant_record = EmissionsRecord.objects.create(
            plant=self.plant,
            timestamp=timezone.now(),
            nox_ppm=Decimal('120.00'),
            co2_tonnes=Decimal('350.00'),
            sox_ppm=Decimal('80.00'),
            is_compliant=True,
        )

    def test_emissions_creation(self):
        self.assertEqual(self.compliant_record.plant, self.plant)
        self.assertEqual(self.compliant_record.nox_ppm, Decimal('120.00'))
        self.assertEqual(self.compliant_record.co2_tonnes, Decimal('350.00'))
        self.assertEqual(self.compliant_record.sox_ppm, Decimal('80.00'))

    def test_emissions_default_limits(self):
        self.assertEqual(self.compliant_record.nox_limit, Decimal('200'))
        self.assertEqual(self.compliant_record.co2_limit, Decimal('500'))
        self.assertEqual(self.compliant_record.sox_limit, Decimal('150'))

    def test_emissions_compliant_str(self):
        self.assertIn('Compliant', str(self.compliant_record))
        self.assertIn('RISHA', str(self.compliant_record))

    def test_emissions_noncompliant_str(self):
        noncompliant = EmissionsRecord.objects.create(
            plant=self.plant,
            timestamp=timezone.now(),
            nox_ppm=Decimal('250.00'),
            co2_tonnes=Decimal('600.00'),
            sox_ppm=Decimal('180.00'),
            is_compliant=False,
        )
        self.assertIn('EXCEEDS LIMITS', str(noncompliant))

    def test_emissions_default_compliant(self):
        record = EmissionsRecord.objects.create(
            plant=self.plant,
            timestamp=timezone.now(),
            nox_ppm=Decimal('100.00'),
            co2_tonnes=Decimal('200.00'),
            sox_ppm=Decimal('50.00'),
        )
        self.assertTrue(record.is_compliant)


class DemandForecastModelTest(TestCase):
    """Tests for the DemandForecast model."""

    def setUp(self):
        now = timezone.now()
        self.forecast = DemandForecast.objects.create(
            timestamp=now,
            forecast_hour=now + timedelta(hours=1),
            predicted_mw=Decimal('2500.00'),
            confidence_lower=Decimal('2300.00'),
            confidence_upper=Decimal('2700.00'),
        )

    def test_forecast_creation(self):
        self.assertEqual(self.forecast.predicted_mw, Decimal('2500.00'))
        self.assertEqual(self.forecast.confidence_lower, Decimal('2300.00'))
        self.assertEqual(self.forecast.confidence_upper, Decimal('2700.00'))

    def test_forecast_str(self):
        self.assertIn('2500.00', str(self.forecast))
        self.assertIn('MW', str(self.forecast))

    def test_forecast_default_model_version(self):
        self.assertEqual(self.forecast.model_version, 'v1.0')

    def test_forecast_actual_mw_nullable(self):
        self.assertIsNone(self.forecast.actual_mw)
        self.forecast.actual_mw = Decimal('2480.00')
        self.forecast.save()
        self.forecast.refresh_from_db()
        self.assertEqual(self.forecast.actual_mw, Decimal('2480.00'))


class HeatRateRecordModelTest(TestCase):
    """Tests for the HeatRateRecord model."""

    def setUp(self):
        self.plant = Plant.objects.create(
            code='AMMAN',
            name='Amman East Power Plant',
            plant_type=Plant.PlantType.CCGT,
            capacity_mw=Decimal('370.00'),
        )
        self.record = HeatRateRecord.objects.create(
            plant=self.plant,
            timestamp=timezone.now(),
            heat_rate_btu_kwh=Decimal('7500.00'),
            fuel_consumption_kg=Decimal('12000.00'),
            power_output_mw=Decimal('350.00'),
        )

    def test_heat_rate_creation(self):
        self.assertEqual(self.record.plant, self.plant)
        self.assertEqual(self.record.heat_rate_btu_kwh, Decimal('7500.00'))
        self.assertEqual(self.record.fuel_consumption_kg, Decimal('12000.00'))
        self.assertEqual(self.record.power_output_mw, Decimal('350.00'))

    def test_heat_rate_str(self):
        self.assertIn('AMMAN', str(self.record))
        self.assertIn('7500.00', str(self.record))
        self.assertIn('BTU/kWh', str(self.record))

    def test_heat_rate_ambient_temp_nullable(self):
        self.assertIsNone(self.record.ambient_temp_c)
