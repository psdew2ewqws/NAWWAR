"""
PlantSimulator base class - Common logic for generating realistic sensor data.
"""
import math
import random
from dataclasses import dataclass
from datetime import datetime

from .weather import generate_weather, WeatherData


@dataclass
class TurbineSpec:
    """Configuration for a single turbine."""
    turbine_id: str
    capacity_mw: float
    base_vibration: float       # mm/s nominal
    base_temperature: float     # °C nominal
    base_pressure: float        # bar nominal
    base_rpm: float             # nominal RPM
    base_exhaust_temp: float    # °C nominal


@dataclass
class SensorSnapshot:
    """All sensor values for one turbine at one point in time."""
    turbine_id: str
    timestamp: datetime
    vibration_mm_s: float
    temperature_c: float
    pressure_bar: float
    rpm: float
    exhaust_temp_c: float
    is_anomaly: bool = False
    anomaly_score: float = 0.0


class PlantSimulator:
    """
    Base simulator for a CEGCO power plant.

    Subclasses define plant-specific turbine specs and behavior.
    Generates realistic time-series sensor data with:
    - Diurnal load patterns (grid demand)
    - Ambient temperature effects
    - Random operational noise
    - Optional anomaly injection (bearing degradation)
    """

    plant_code: str = ''
    plant_type: str = ''
    turbines: list[TurbineSpec] = []

    # Anomaly config: map of turbine_id -> (start_day_offset, degradation_rate)
    # Applied as gradual vibration increase
    _anomaly_turbines: dict[str, tuple[int, float]] = {}

    def __init__(self, anomaly_turbines: dict[str, tuple[int, float]] | None = None):
        if anomaly_turbines is not None:
            self._anomaly_turbines = anomaly_turbines

    def _load_factor(self, hour: int) -> float:
        """
        Grid demand load factor by hour of day.
        Peak: 12:00-17:00 (~0.85-0.95)
        Off-peak: 00:00-06:00 (~0.45-0.60)
        """
        if 0 <= hour < 6:
            return 0.50 + 0.05 * math.sin(math.pi * hour / 6)
        elif 6 <= hour < 12:
            return 0.55 + 0.35 * ((hour - 6) / 6)
        elif 12 <= hour < 17:
            return 0.85 + 0.10 * math.sin(math.pi * (hour - 12) / 5)
        elif 17 <= hour < 21:
            return 0.90 - 0.20 * ((hour - 17) / 4)
        else:
            return 0.70 - 0.15 * ((hour - 21) / 3)

    def generate_hour(
        self,
        dt: datetime,
        day_offset: int = 0,
    ) -> list[SensorSnapshot]:
        """
        Generate sensor snapshots for all turbines at a given hour.

        Args:
            dt: The datetime for the reading.
            day_offset: Days since simulation start (for anomaly progression).
        """
        weather = generate_weather(self.plant_code, dt)
        load = self._load_factor(dt.hour) + random.gauss(0, 0.03)
        load = max(0.30, min(1.0, load))

        snapshots = []
        for spec in self.turbines:
            snapshot = self._generate_turbine_reading(spec, dt, weather, load, day_offset)
            snapshots.append(snapshot)
        return snapshots

    def _generate_turbine_reading(
        self,
        spec: TurbineSpec,
        dt: datetime,
        weather: WeatherData,
        load_factor: float,
        day_offset: int,
    ) -> SensorSnapshot:
        """Generate a single reading for one turbine."""
        # Ambient temperature effect on performance
        ambient_effect = (weather.temperature_c - 25) / 100  # normalized

        # Vibration: base + load effect + noise
        vibration = spec.base_vibration * (0.8 + 0.4 * load_factor)
        vibration += random.gauss(0, spec.base_vibration * 0.08)

        # Temperature: increases with load and ambient
        temperature = spec.base_temperature * (0.85 + 0.20 * load_factor)
        temperature += ambient_effect * 15
        temperature += random.gauss(0, 3)

        # Pressure: fairly stable, slight load dependence
        pressure = spec.base_pressure * (0.95 + 0.08 * load_factor)
        pressure += random.gauss(0, spec.base_pressure * 0.02)

        # RPM: very stable under normal conditions
        rpm = spec.base_rpm * (0.998 + 0.004 * load_factor)
        rpm += random.gauss(0, spec.base_rpm * 0.001)

        # Exhaust temp: strongly load-dependent
        exhaust_temp = spec.base_exhaust_temp * (0.80 + 0.25 * load_factor)
        exhaust_temp += ambient_effect * 10
        exhaust_temp += random.gauss(0, 5)

        # Anomaly injection: gradual bearing degradation
        is_anomaly = False
        anomaly_score = 0.0
        if spec.turbine_id in self._anomaly_turbines:
            start_day, rate = self._anomaly_turbines[spec.turbine_id]
            if day_offset >= start_day:
                days_degrading = day_offset - start_day
                # Exponential-ish growth in vibration
                degradation = rate * (days_degrading ** 1.5)
                vibration += degradation
                # Rising exhaust temp as bearing friction increases
                exhaust_temp += degradation * 8
                # Mark as anomaly once vibration exceeds warning threshold
                if vibration > 4.5:
                    is_anomaly = True
                    anomaly_score = min(1.0, (vibration - 4.5) / (11.2 - 4.5))

        return SensorSnapshot(
            turbine_id=spec.turbine_id,
            timestamp=dt,
            vibration_mm_s=round(max(0.1, vibration), 4),
            temperature_c=round(temperature, 2),
            pressure_bar=round(max(1, pressure), 2),
            rpm=round(rpm, 1),
            exhaust_temp_c=round(exhaust_temp, 2),
            is_anomaly=is_anomaly,
            anomaly_score=round(anomaly_score, 4),
        )

    def generate_emissions(
        self,
        dt: datetime,
        load_factor: float | None = None,
    ) -> dict:
        """Generate emissions data for the plant at a given hour."""
        if load_factor is None:
            load_factor = self._load_factor(dt.hour) + random.gauss(0, 0.03)
            load_factor = max(0.30, min(1.0, load_factor))

        # NOx: increases with load, typical range 50-180 ppm
        nox = 60 + 100 * load_factor + random.gauss(0, 10)
        # CO2: proportional to fuel burn
        total_cap = sum(t.capacity_mw for t in self.turbines)
        co2 = total_cap * load_factor * 0.85 + random.gauss(0, 5)
        # SOx: mainly from HFO plants
        sox_base = 80 if 'HFO' in getattr(self, 'fuel_type', '') else 30
        sox = sox_base * load_factor + random.gauss(0, 8)

        nox_limit = 200.0
        co2_limit = total_cap * 1.2
        sox_limit = 150.0

        is_compliant = nox <= nox_limit and co2 <= co2_limit and sox <= sox_limit

        # Occasionally exceed limits (~3% chance)
        if random.random() < 0.03:
            nox += random.uniform(20, 60)
            is_compliant = False

        return {
            'nox_ppm': round(max(0, nox), 2),
            'co2_tonnes': round(max(0, co2), 2),
            'sox_ppm': round(max(0, sox), 2),
            'nox_limit': nox_limit,
            'co2_limit': round(co2_limit, 2),
            'sox_limit': sox_limit,
            'is_compliant': is_compliant,
        }

    def generate_heat_rate(
        self,
        dt: datetime,
        ambient_temp_c: float,
        load_factor: float | None = None,
    ) -> dict:
        """Generate heat rate data for the plant."""
        if load_factor is None:
            load_factor = self._load_factor(dt.hour) + random.gauss(0, 0.03)
            load_factor = max(0.30, min(1.0, load_factor))

        total_cap = sum(t.capacity_mw for t in self.turbines)
        power_output = total_cap * load_factor

        # Heat rate: better (lower) at higher loads, worse at part-load
        # Typical range: 8500-11000 BTU/kWh
        base_hr = {'steam': 10200, 'gas': 9800, 'ccgt': 7200}
        hr = base_hr.get(self.plant_type, 9500)
        # Part-load penalty
        hr *= (1.3 - 0.35 * load_factor)
        # Ambient temperature penalty (higher ambient = worse efficiency)
        hr += (ambient_temp_c - 25) * 5
        hr += random.gauss(0, 100)

        # Fuel consumption (kg/h): derived from heat rate and output
        # 1 kg natural gas ≈ 48,000 BTU; 1 kg HFO ≈ 40,000 BTU
        btu_per_kg = 45000
        fuel_kg = (hr * power_output * 1000) / btu_per_kg

        return {
            'heat_rate_btu_kwh': round(max(6000, hr), 2),
            'fuel_consumption_kg': round(max(0, fuel_kg), 2),
            'power_output_mw': round(power_output, 2),
            'ambient_temp_c': round(ambient_temp_c, 2),
        }
