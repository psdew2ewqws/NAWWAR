"""
Rehab Combined Cycle Power Station simulator.

297 MW CCGT plant, 6 turbines (H1-H6), commissioned 1990.
Natural gas. Combined cycle: gas turbines + steam recovery turbines.
H1-H4 are gas turbines, H5-H6 are steam turbines (HRSG).
"""
from .base import PlantSimulator, TurbineSpec


class RehabSimulator(PlantSimulator):
    """Simulator for Rehab Combined Cycle Power Station."""

    plant_code = 'REHAB'
    plant_type = 'ccgt'
    fuel_type = 'natural gas'

    turbines = [
        # Gas turbines (GT section)
        TurbineSpec(
            turbine_id='H1',
            capacity_mw=55.0,
            base_vibration=1.4,      # mm/s
            base_temperature=360.0,  # °C - compressor discharge
            base_pressure=35.0,      # bar
            base_rpm=5100.0,         # gas turbine RPM
            base_exhaust_temp=560.0, # °C - feeds HRSG
        ),
        TurbineSpec(
            turbine_id='H2',
            capacity_mw=55.0,
            base_vibration=1.3,
            base_temperature=358.0,
            base_pressure=34.5,
            base_rpm=5100.0,
            base_exhaust_temp=555.0,
        ),
        TurbineSpec(
            turbine_id='H3',
            capacity_mw=55.0,
            base_vibration=1.5,
            base_temperature=365.0,
            base_pressure=36.0,
            base_rpm=5100.0,
            base_exhaust_temp=565.0,
        ),
        TurbineSpec(
            turbine_id='H4',
            capacity_mw=55.0,
            base_vibration=1.2,
            base_temperature=355.0,
            base_pressure=34.0,
            base_rpm=5100.0,
            base_exhaust_temp=550.0,
        ),
        # Steam turbines (ST section - fed by HRSG)
        TurbineSpec(
            turbine_id='H5',
            capacity_mw=38.5,
            base_vibration=1.6,      # steam turbine
            base_temperature=510.0,  # °C - HP steam inlet
            base_pressure=85.0,      # bar - HP steam
            base_rpm=3000.0,         # synchronous speed 50Hz
            base_exhaust_temp=380.0, # °C - LP exhaust to condenser
        ),
        TurbineSpec(
            turbine_id='H6',
            capacity_mw=38.5,
            base_vibration=1.7,
            base_temperature=505.0,
            base_pressure=83.0,
            base_rpm=3000.0,
            base_exhaust_temp=375.0,
        ),
    ]
