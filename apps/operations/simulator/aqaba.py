"""
Aqaba Thermal Power Station simulator.

390 MW steam plant, 5 turbines (A1-A5), commissioned 1985.
Multi-fuel (HFO/natural gas). Higher vibration variance due to age.
"""
from .base import PlantSimulator, TurbineSpec


class AqabaSimulator(PlantSimulator):
    """Simulator for Aqaba Thermal Power Station."""

    plant_code = 'AQABA'
    plant_type = 'steam'
    fuel_type = 'multi-fuel (HFO/natural gas)'

    turbines = [
        TurbineSpec(
            turbine_id='A1',
            capacity_mw=78.0,
            base_vibration=2.2,     # mm/s - older unit, higher baseline
            base_temperature=480.0,  # °C - steam inlet temp
            base_pressure=100.0,     # bar - HP steam
            base_rpm=3000.0,         # synchronous speed 50Hz
            base_exhaust_temp=420.0, # °C - LP exhaust
        ),
        TurbineSpec(
            turbine_id='A2',
            capacity_mw=78.0,
            base_vibration=1.9,
            base_temperature=485.0,
            base_pressure=102.0,
            base_rpm=3000.0,
            base_exhaust_temp=415.0,
        ),
        TurbineSpec(
            turbine_id='A3',
            capacity_mw=78.0,
            base_vibration=2.5,     # oldest unit, highest vibration
            base_temperature=475.0,
            base_pressure=98.0,
            base_rpm=3000.0,
            base_exhaust_temp=425.0,
        ),
        TurbineSpec(
            turbine_id='A4',
            capacity_mw=78.0,
            base_vibration=1.8,
            base_temperature=490.0,
            base_pressure=105.0,
            base_rpm=3000.0,
            base_exhaust_temp=410.0,
        ),
        TurbineSpec(
            turbine_id='A5',
            capacity_mw=78.0,
            base_vibration=2.0,
            base_temperature=482.0,
            base_pressure=101.0,
            base_rpm=3000.0,
            base_exhaust_temp=418.0,
        ),
    ]
