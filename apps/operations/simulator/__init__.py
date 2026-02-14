"""
Operations simulator package.
Generates realistic power plant sensor data for Nawwar AI.
"""
from .base import PlantSimulator, TurbineSpec, SensorSnapshot
from .aqaba import AqabaSimulator
from .risha import RishaSimulator
from .rehab import RehabSimulator
from .weather import generate_weather, WeatherData

__all__ = [
    'PlantSimulator',
    'TurbineSpec',
    'SensorSnapshot',
    'AqabaSimulator',
    'RishaSimulator',
    'RehabSimulator',
    'generate_weather',
    'WeatherData',
]
