"""
Management command to generate realistic plant data for 30 days.

Creates plants, turbines, sensor readings, emissions, and heat rate records.
Injects bearing degradation anomalies on 2-3 turbines.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.operations.models import (
    Plant,
    Turbine,
    SensorReading,
    EmissionsRecord,
    HeatRateRecord,
    DemandForecast,
    MaintenancePrediction,
)
from apps.operations.simulator import (
    AqabaSimulator,
    RishaSimulator,
    RehabSimulator,
    generate_weather,
)


SIMULATOR_MAP = {
    'AQABA': AqabaSimulator,
    'RISHA': RishaSimulator,
    'REHAB': RehabSimulator,
}

# Anomaly injection: bearing degradation on these turbines
# (start_day_offset, degradation_rate)
ANOMALY_CONFIG = {
    'AQABA': {'A3': (25, 0.35)},          # old unit, last 5 days
    'RISHA': {'R2': (26, 0.28)},          # last 4 days
    'REHAB': {'H5': (25, 0.30)},          # steam turbine, last 5 days
}


class Command(BaseCommand):
    help = 'Generate 30 days of realistic plant sensor data with anomaly injection.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of data to generate (default: 30).',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating.',
        )

    def handle(self, *args, **options):
        days = options['days']
        if options['clear']:
            self._clear_data()

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        start = now - timedelta(days=days)

        # Create plants and turbines
        plants = self._create_plants()
        turbine_map = self._create_turbines(plants)

        # Generate data for each plant
        for plant_code, plant in plants.items():
            self.stdout.write(f'\nGenerating data for {plant_code}...')

            sim_class = SIMULATOR_MAP[plant_code]
            anomalies = ANOMALY_CONFIG.get(plant_code, {})
            sim = sim_class(anomaly_turbines=anomalies)

            readings_batch = []
            emissions_batch = []
            heat_rate_batch = []

            turbines = turbine_map[plant_code]

            for day in range(days):
                dt_day = start + timedelta(days=day)

                for hour in range(24):
                    dt = dt_day.replace(hour=hour)

                    # Sensor readings
                    snapshots = sim.generate_hour(dt, day_offset=day)
                    for snap in snapshots:
                        turbine = turbines[snap.turbine_id]
                        for reading_type, value, unit in [
                            ('vibration', snap.vibration_mm_s, 'mm/s'),
                            ('temperature', snap.temperature_c, '°C'),
                            ('pressure', snap.pressure_bar, 'bar'),
                            ('rpm', snap.rpm, 'rpm'),
                            ('exhaust_temp', snap.exhaust_temp_c, '°C'),
                        ]:
                            readings_batch.append(SensorReading(
                                turbine=turbine,
                                timestamp=dt,
                                reading_type=reading_type,
                                value=Decimal(str(value)),
                                unit=unit,
                                is_anomaly=snap.is_anomaly if reading_type == 'vibration' else False,
                                anomaly_score=snap.anomaly_score if reading_type == 'vibration' else None,
                            ))

                    # Emissions (hourly)
                    em_data = sim.generate_emissions(dt)
                    emissions_batch.append(EmissionsRecord(
                        plant=plant,
                        timestamp=dt,
                        nox_ppm=Decimal(str(em_data['nox_ppm'])),
                        co2_tonnes=Decimal(str(em_data['co2_tonnes'])),
                        sox_ppm=Decimal(str(em_data['sox_ppm'])),
                        nox_limit=Decimal(str(em_data['nox_limit'])),
                        co2_limit=Decimal(str(em_data['co2_limit'])),
                        sox_limit=Decimal(str(em_data['sox_limit'])),
                        is_compliant=em_data['is_compliant'],
                    ))

                    # Heat rate (hourly)
                    weather = generate_weather(plant_code, dt)
                    hr_data = sim.generate_heat_rate(dt, weather.temperature_c)
                    heat_rate_batch.append(HeatRateRecord(
                        plant=plant,
                        timestamp=dt,
                        heat_rate_btu_kwh=Decimal(str(hr_data['heat_rate_btu_kwh'])),
                        fuel_consumption_kg=Decimal(str(hr_data['fuel_consumption_kg'])),
                        power_output_mw=Decimal(str(hr_data['power_output_mw'])),
                        ambient_temp_c=Decimal(str(hr_data['ambient_temp_c'])),
                    ))

                if (day + 1) % 5 == 0:
                    self.stdout.write(f'  Day {day + 1}/{days} complete')

            # Bulk create
            self.stdout.write(f'  Saving {len(readings_batch)} sensor readings...')
            SensorReading.objects.bulk_create(readings_batch, batch_size=5000)

            self.stdout.write(f'  Saving {len(emissions_batch)} emissions records...')
            EmissionsRecord.objects.bulk_create(emissions_batch, batch_size=2000)

            self.stdout.write(f'  Saving {len(heat_rate_batch)} heat rate records...')
            HeatRateRecord.objects.bulk_create(heat_rate_batch, batch_size=2000)

        # Generate demand forecasts
        self._generate_forecasts(start, now, days)

        # Generate maintenance predictions for anomaly turbines
        self._generate_predictions(turbine_map, now)

        # Update plant stats
        self._update_plant_stats(plants)

        self.stdout.write(self.style.SUCCESS('\nData generation complete!'))
        self._print_summary()

    def _clear_data(self):
        self.stdout.write('Clearing existing data...')
        SensorReading.objects.all().delete()
        EmissionsRecord.objects.all().delete()
        HeatRateRecord.objects.all().delete()
        DemandForecast.objects.all().delete()
        MaintenancePrediction.objects.all().delete()
        Turbine.objects.all().delete()
        Plant.objects.all().delete()

    def _create_plants(self) -> dict[str, Plant]:
        plants = {}
        for code, cfg in settings.CEGCO_PLANTS.items():
            plant, created = Plant.objects.update_or_create(
                code=code,
                defaults={
                    'name': cfg['name'],
                    'name_ar': cfg['name_ar'],
                    'plant_type': cfg['type'],
                    'fuel_type': cfg['fuel'],
                    'capacity_mw': cfg['capacity_mw'],
                    'commissioned_year': cfg['year'],
                    'latitude': cfg['location']['lat'],
                    'longitude': cfg['location']['lon'],
                    'status': Plant.Status.ONLINE,
                    'is_active': True,
                },
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'  {action} plant: {plant}')
            plants[code] = plant
        return plants

    def _create_turbines(self, plants: dict[str, Plant]) -> dict[str, dict[str, Turbine]]:
        turbine_map = {}
        for code, sim_class in SIMULATOR_MAP.items():
            plant = plants[code]
            sim = sim_class()
            turbine_map[code] = {}
            for spec in sim.turbines:
                turbine, created = Turbine.objects.update_or_create(
                    plant=plant,
                    turbine_id=spec.turbine_id,
                    defaults={
                        'name': f'{plant.name} - Unit {spec.turbine_id}',
                        'capacity_mw': spec.capacity_mw,
                        'status': Turbine.Status.ONLINE,
                        'hours_since_maintenance': random.randint(1000, 8000),
                    },
                )
                turbine_map[code][spec.turbine_id] = turbine
        return turbine_map

    def _generate_forecasts(self, start, now, days):
        self.stdout.write('\nGenerating demand forecasts...')
        forecasts = []
        total_capacity = sum(
            cfg['capacity_mw'] for cfg in settings.CEGCO_PLANTS.values()
        )

        for day in range(days):
            dt_day = start + timedelta(days=day)
            for hour in range(24):
                forecast_hour = dt_day.replace(hour=hour)
                # Demand follows typical grid pattern
                base = total_capacity * 0.6
                if 12 <= hour <= 17:
                    base = total_capacity * 0.85
                elif 6 <= hour <= 22:
                    base = total_capacity * 0.70

                predicted = base + random.gauss(0, total_capacity * 0.05)
                actual = predicted + random.gauss(0, total_capacity * 0.03)
                margin = total_capacity * 0.08

                forecasts.append(DemandForecast(
                    timestamp=forecast_hour - timedelta(hours=24),
                    forecast_hour=forecast_hour,
                    predicted_mw=Decimal(str(round(max(0, predicted), 2))),
                    actual_mw=Decimal(str(round(max(0, actual), 2))),
                    confidence_lower=Decimal(str(round(max(0, predicted - margin), 2))),
                    confidence_upper=Decimal(str(round(predicted + margin, 2))),
                    model_version='v1.0',
                ))

        DemandForecast.objects.bulk_create(forecasts, batch_size=5000)
        self.stdout.write(f'  Created {len(forecasts)} demand forecasts')

    def _generate_predictions(self, turbine_map, now):
        self.stdout.write('\nGenerating maintenance predictions for anomaly turbines...')
        predictions = []
        for plant_code, anomalies in ANOMALY_CONFIG.items():
            for turbine_id in anomalies:
                turbine = turbine_map[plant_code][turbine_id]
                predictions.append(MaintenancePrediction(
                    turbine=turbine,
                    prediction_type=MaintenancePrediction.PredictionType.BEARING,
                    confidence=round(random.uniform(0.78, 0.95), 2),
                    predicted_failure_date=(now + timedelta(days=random.randint(5, 15))).date(),
                    severity=MaintenancePrediction.Severity.HIGH,
                    description=(
                        f'Bearing degradation detected on {turbine}. '
                        f'Vibration trending upward over last 5 days.'
                    ),
                    description_ar=(
                        f'تم اكتشاف تدهور في المحمل على {turbine}. '
                        f'الاهتزاز في ازدياد خلال الأيام الخمسة الأخيرة.'
                    ),
                    recommended_action=(
                        'Schedule bearing inspection and replacement within 2 weeks. '
                        'Monitor vibration levels closely.'
                    ),
                    recommended_action_ar=(
                        'جدولة فحص واستبدال المحمل خلال أسبوعين. '
                        'مراقبة مستويات الاهتزاز عن كثب.'
                    ),
                ))
        MaintenancePrediction.objects.bulk_create(predictions)
        self.stdout.write(f'  Created {len(predictions)} maintenance predictions')

    def _update_plant_stats(self, plants):
        for code, plant in plants.items():
            sim_class = SIMULATOR_MAP[code]
            sim = sim_class()
            total_cap = sum(t.capacity_mw for t in sim.turbines)
            load = total_cap * random.uniform(0.65, 0.85)
            efficiency = random.uniform(32, 42) if plant.plant_type != 'ccgt' else random.uniform(48, 56)
            plant.current_load_mw = Decimal(str(round(load, 2)))
            plant.efficiency_percent = Decimal(str(round(efficiency, 2)))
            plant.save(update_fields=['current_load_mw', 'efficiency_percent'])

    def _print_summary(self):
        self.stdout.write('\n--- Summary ---')
        self.stdout.write(f'Plants: {Plant.objects.count()}')
        self.stdout.write(f'Turbines: {Turbine.objects.count()}')
        self.stdout.write(f'Sensor Readings: {SensorReading.objects.count()}')
        self.stdout.write(f'Emissions Records: {EmissionsRecord.objects.count()}')
        self.stdout.write(f'Heat Rate Records: {HeatRateRecord.objects.count()}')
        self.stdout.write(f'Demand Forecasts: {DemandForecast.objects.count()}')
        self.stdout.write(f'Maintenance Predictions: {MaintenancePrediction.objects.count()}')
        anomaly_count = SensorReading.objects.filter(is_anomaly=True).count()
        self.stdout.write(f'Anomalous Readings: {anomaly_count}')
