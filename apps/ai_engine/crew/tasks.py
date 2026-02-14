"""
CrewAI task definitions for the Nawwar platform.

Tasks define the specific work that agents perform. Each task has a
description template, expected output format, and is assigned to an agent.
"""
from crewai import Task, Agent


def create_bill_analysis_task(*, agent: Agent, subscriber_number: str) -> Task:
    """Create a task to analyze a consumer's electricity bill."""
    return Task(
        description=(
            f"Analyze the electricity bills for subscriber number {subscriber_number}. "
            "Look up their recent bills, examine the consumption patterns, check the "
            "applicable tariff tiers, and identify any anomalies or unusual charges. "
            "Provide a clear Arabic summary of the bill analysis including:\n"
            "1. Total consumption and cost trends over recent months\n"
            "2. Which tariff tier(s) the consumer falls into\n"
            "3. Any anomalies or unusually high charges\n"
            "4. Comparison with typical usage for their sector"
        ),
        expected_output=(
            "A structured Arabic report with: consumption summary, tier breakdown, "
            "anomaly flags, and a plain-language explanation of the bill."
        ),
        agent=agent,
    )


def create_savings_recommendation_task(*, agent: Agent, subscriber_number: str) -> Task:
    """Create a task to generate personalized savings recommendations."""
    return Task(
        description=(
            f"Generate personalized energy savings recommendations for subscriber "
            f"{subscriber_number}. Analyze their consumption patterns, check current "
            "tariff rates, consider weather impacts, and provide specific actionable advice. "
            "Focus on:\n"
            "1. Load shifting opportunities (peak vs off-peak)\n"
            "2. Tier reduction strategies\n"
            "3. Appliance-specific recommendations (AC, water heater, lighting)\n"
            "4. Estimated savings in JOD for each recommendation\n"
            "Provide all recommendations in Arabic."
        ),
        expected_output=(
            "A list of 3-5 specific, actionable energy saving recommendations in Arabic, "
            "each with estimated monthly savings in JOD."
        ),
        agent=agent,
    )


def create_compliance_check_task(*, agent: Agent, subscriber_number: str = "") -> Task:
    """Create a task to check regulatory compliance."""
    return Task(
        description=(
            "Review regulatory compliance status. Check that tariff rates comply with "
            "EMRC regulations and that consumer billing follows the approved rate schedule. "
            f"{'Focus on subscriber ' + subscriber_number + '.' if subscriber_number else ''} "
            "Verify:\n"
            "1. Tariff tiers match EMRC-approved rates\n"
            "2. Time-of-use multipliers are correctly applied\n"
            "3. Any applicable subsidies or discounts are properly reflected\n"
            "Provide findings in Arabic."
        ),
        expected_output=(
            "A compliance status report in Arabic covering tariff accuracy, "
            "billing rule adherence, and any regulatory flags."
        ),
        agent=agent,
    )


def create_maintenance_diagnosis_task(*, agent: Agent, plant_code: str, turbine_id: int = 0) -> Task:
    """Create a task to diagnose maintenance needs."""
    return Task(
        description=(
            f"Analyze the maintenance status for plant {plant_code}"
            f"{' turbine ' + str(turbine_id) if turbine_id else ''}. "
            "Review sensor readings, check active maintenance predictions, and provide "
            "a diagnosis. Include:\n"
            "1. Current sensor reading analysis (temperature, vibration, pressure)\n"
            "2. Active maintenance predictions and their severity\n"
            "3. Recommended immediate actions\n"
            "4. Suggested maintenance schedule adjustments\n"
            "Provide the report in Arabic."
        ),
        expected_output=(
            "A maintenance diagnosis report in Arabic with sensor analysis, "
            "risk assessment, and prioritized action items."
        ),
        agent=agent,
    )


def create_demand_forecast_task(*, agent: Agent, hours: int = 24) -> Task:
    """Create a task to analyze demand forecasts."""
    return Task(
        description=(
            f"Analyze the electricity demand forecast for the next {hours} hours. "
            "Check current weather conditions and correlate with demand patterns. "
            "Provide:\n"
            "1. Expected peak demand and timing\n"
            "2. Weather impact analysis\n"
            "3. Recommended generation dispatch adjustments\n"
            "4. Risk of demand exceeding capacity\n"
            "Provide the analysis in Arabic."
        ),
        expected_output=(
            "A demand forecast analysis in Arabic with peak timing, weather correlation, "
            "and dispatch recommendations."
        ),
        agent=agent,
    )


def create_emissions_monitoring_task(*, agent: Agent, plant_code: str) -> Task:
    """Create a task to monitor emissions compliance."""
    return Task(
        description=(
            f"Monitor and analyze emissions data for plant {plant_code}. "
            "Review recent CO2, NOx, and SO2 readings against regulatory limits. "
            "Provide:\n"
            "1. Current emissions levels vs EMRC limits\n"
            "2. Trend analysis (improving or worsening)\n"
            "3. Any threshold violations or warnings\n"
            "4. Recommended corrective actions if needed\n"
            "Provide the report in Arabic."
        ),
        expected_output=(
            "An emissions compliance report in Arabic with current levels, "
            "regulatory comparison, and any required actions."
        ),
        agent=agent,
    )
