"""
Risha Gas Power Station simulator.

150 MW gas turbine plant, 4 turbines (R1-R4), commissioned 1989.
Natural gas fuel. Desert location with high ambient temperatures.
"""
from .base import PlantSimulator, TurbineSpec


class RishaSimulator(PlantSimulator):
    """Simulator for Risha Gas Power Station."""

    plant_code = 'RISHA'
    plant_type = 'gas'
    fuel_type = 'natural gas'

    turbines = [
        TurbineSpec(
            turbine_id='R1',
            capacity_mw=37.5,
            base_vibration=1.5,      # mm/s - gas turbine, lower baseline
            base_temperature=350.0,  # °C - compressor discharge temp
            base_pressure=32.0,      # bar - compressor outlet
            base_rpm=5100.0,         # gas turbine RPM
            base_exhaust_temp=540.0, # °C - gas turbine exhaust
        ),
        TurbineSpec(
            turbine_id='R2',
            capacity_mw=37.5,
            base_vibration=1.4,
            base_temperature=345.0,
            base_pressure=31.5,
            base_rpm=5100.0,
            base_exhaust_temp=535.0,
        ),
        TurbineSpec(
            turbine_id='R3',
            capacity_mw=37.5,
            base_vibration=1.6,
            base_temperature=355.0,
            base_pressure=33.0,
            base_rpm=5100.0,
            base_exhaust_temp=545.0,
        ),
        TurbineSpec(
            turbine_id='R4',
            capacity_mw=37.5,
            base_vibration=1.3,
            base_temperature=348.0,
            base_pressure=32.5,
            base_rpm=5100.0,
            base_exhaust_temp=530.0,
        ),
    ]
