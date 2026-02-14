"""
Weather simulator - Generates realistic weather data for Jordanian plant locations.
"""
import math
import random
from dataclasses import dataclass
from datetime import datetime


@dataclass
class WeatherData:
    """Weather conditions at a specific time and location."""
    temperature_c: float
    humidity_percent: float
    wind_speed_ms: float
    pressure_hpa: float


# Location-specific climate baselines
LOCATION_CLIMATE = {
    'AQABA': {
        'summer_avg_c': 39.0,
        'winter_avg_c': 16.0,
        'humidity_base': 30,
        'wind_base_ms': 4.5,
    },
    'RISHA': {
        'summer_avg_c': 42.0,
        'winter_avg_c': 8.0,
        'humidity_base': 20,
        'wind_base_ms': 5.0,
    },
    'REHAB': {
        'summer_avg_c': 34.0,
        'winter_avg_c': 6.0,
        'humidity_base': 45,
        'wind_base_ms': 3.5,
    },
}


def generate_weather(plant_code: str, dt: datetime) -> WeatherData:
    """
    Generate realistic weather data for a given plant location and time.

    Uses sinusoidal seasonal and diurnal patterns with random noise.
    """
    climate = LOCATION_CLIMATE.get(plant_code, LOCATION_CLIMATE['REHAB'])

    # Day of year for seasonal cycle (0 = Jan 1)
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour

    # Seasonal temperature: sinusoidal with peak in July (day ~200)
    seasonal_factor = math.sin(2 * math.pi * (day_of_year - 80) / 365)
    avg_temp = (climate['summer_avg_c'] + climate['winter_avg_c']) / 2
    temp_amplitude = (climate['summer_avg_c'] - climate['winter_avg_c']) / 2
    base_temp = avg_temp + temp_amplitude * seasonal_factor

    # Diurnal cycle: peak at 14:00, min at 05:00
    diurnal_factor = math.sin(2 * math.pi * (hour - 5) / 24)
    diurnal_amplitude = 6.0 + 2.0 * max(0, seasonal_factor)
    temp = base_temp + diurnal_amplitude * diurnal_factor + random.gauss(0, 1.5)

    # Humidity: inversely correlated with temperature
    humidity = climate['humidity_base'] - 10 * seasonal_factor - 5 * diurnal_factor
    humidity += random.gauss(0, 5)
    humidity = max(10, min(95, humidity))

    # Wind: slightly stronger in afternoon, with random gusts
    wind = climate['wind_base_ms'] + 1.5 * max(0, diurnal_factor) + random.gauss(0, 1.0)
    wind = max(0.5, wind)

    # Atmospheric pressure
    pressure = 1013.25 - 3 * seasonal_factor + random.gauss(0, 2)

    return WeatherData(
        temperature_c=round(temp, 1),
        humidity_percent=round(humidity, 1),
        wind_speed_ms=round(wind, 1),
        pressure_hpa=round(pressure, 1),
    )
