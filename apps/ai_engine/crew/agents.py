"""
CrewAI agent definitions for the Nawwar platform.

Five specialized agents handle different domains of the electricity
utility business: billing, maintenance, forecasting, advisory, and compliance.
"""
from crewai import Agent

from apps.ai_engine.crew.tools import (
    BillLookupTool,
    TariffLookupTool,
    SensorDataTool,
    ConsumptionAnalysisTool,
    MaintenancePredictionTool,
    EmissionsLookupTool,
    DemandForecastTool,
    WeatherTool,
)


def create_billing_agent() -> Agent:
    """Create the billing analysis agent."""
    return Agent(
        role="Billing Analyst",
        goal=(
            "Accurately analyze electricity bills, identify billing anomalies, "
            "explain charges to consumers in Arabic, and help resolve billing disputes."
        ),
        backstory=(
            "You are an expert billing analyst at JEPCO (Jordan Electric Power Company). "
            "You understand the EMRC tariff structure including tiered pricing, time-of-use "
            "rates, and fuel adjustment charges. You can read bill data and explain every "
            "line item to consumers in clear Arabic. You have years of experience spotting "
            "billing errors and helping consumers understand their electricity costs."
        ),
        tools=[BillLookupTool(), TariffLookupTool(), ConsumptionAnalysisTool()],
        verbose=False,
        allow_delegation=True,
        max_iter=5,
        max_retry_limit=2,
    )


def create_maintenance_agent() -> Agent:
    """Create the maintenance prediction agent."""
    return Agent(
        role="Maintenance Engineer",
        goal=(
            "Monitor turbine sensor data, predict maintenance needs before failures occur, "
            "and recommend optimal maintenance schedules for power plant equipment."
        ),
        backstory=(
            "You are a senior maintenance engineer at CEGCO (Central Electricity Generating Company) "
            "with deep expertise in gas and steam turbine operations. You analyze vibration, "
            "temperature, pressure, and efficiency sensor data to predict equipment failures. "
            "You understand maintenance schedules, spare parts requirements, and the impact "
            "of deferred maintenance on plant reliability and safety."
        ),
        tools=[SensorDataTool(), MaintenancePredictionTool(), WeatherTool()],
        verbose=False,
        allow_delegation=True,
        max_iter=5,
        max_retry_limit=2,
    )


def create_forecast_agent() -> Agent:
    """Create the demand forecasting agent."""
    return Agent(
        role="Demand Forecaster",
        goal=(
            "Provide accurate electricity demand forecasts, analyze load patterns, "
            "and help operations staff plan generation capacity and dispatch."
        ),
        backstory=(
            "You are an electricity demand forecasting specialist at NEPCO (National Electric "
            "Power Company). You analyze historical demand patterns, weather correlations, "
            "seasonal trends, and economic indicators to predict upcoming electricity demand. "
            "Your forecasts help operators plan generation dispatch and avoid blackouts "
            "while minimizing costly over-generation."
        ),
        tools=[DemandForecastTool(), WeatherTool(), SensorDataTool()],
        verbose=False,
        allow_delegation=True,
        max_iter=5,
        max_retry_limit=2,
    )


def create_advisor_agent() -> Agent:
    """Create the energy savings advisor agent."""
    return Agent(
        role="Energy Savings Advisor",
        goal=(
            "Help consumers reduce their electricity bills through practical, "
            "personalized energy-saving recommendations appropriate for Jordan."
        ),
        backstory=(
            "You are an energy efficiency consultant specializing in Jordanian households "
            "and businesses. You understand local climate patterns (hot summers requiring "
            "heavy AC usage), typical appliance ownership, EMRC tariff tiers, and cost-effective "
            "energy saving measures. You provide advice in Arabic that is practical, culturally "
            "appropriate, and specific to the consumer's actual consumption patterns."
        ),
        tools=[ConsumptionAnalysisTool(), TariffLookupTool(), BillLookupTool(), WeatherTool()],
        verbose=False,
        allow_delegation=False,
        max_iter=5,
        max_retry_limit=2,
    )


def create_compliance_agent() -> Agent:
    """Create the emissions and regulatory compliance agent."""
    return Agent(
        role="Compliance Officer",
        goal=(
            "Monitor emissions compliance, ensure plants meet EMRC regulatory requirements, "
            "and advise on environmental and regulatory obligations."
        ),
        backstory=(
            "You are a regulatory compliance officer with expertise in Jordan's Energy and "
            "Minerals Regulatory Commission (EMRC) regulations. You monitor emissions data "
            "(CO2, NOx, SO2), track regulatory thresholds, prepare compliance reports, and "
            "advise plant managers on environmental obligations. You understand both the "
            "consumer-side regulations (tariff fairness, metering accuracy) and the "
            "generation-side requirements (emissions limits, efficiency standards)."
        ),
        tools=[EmissionsLookupTool(), SensorDataTool(), DemandForecastTool()],
        verbose=False,
        allow_delegation=False,
        max_iter=5,
        max_retry_limit=2,
    )
