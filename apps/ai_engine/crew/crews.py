"""
CrewAI crew orchestration for the Nawwar platform.

Two main crews handle different domains:
- consumer_analysis_crew: Consumer-facing billing, savings, and compliance.
- operations_monitoring_crew: Plant maintenance, forecasting, and emissions.
"""
import logging
import signal
import time
from contextlib import contextmanager

from crewai import Crew, Process

from apps.ai_engine.crew.agents import (
    create_billing_agent,
    create_maintenance_agent,
    create_forecast_agent,
    create_advisor_agent,
    create_compliance_agent,
)
from apps.ai_engine.crew.tasks import (
    create_bill_analysis_task,
    create_savings_recommendation_task,
    create_compliance_check_task,
    create_maintenance_diagnosis_task,
    create_demand_forecast_task,
    create_emissions_monitoring_task,
)

logger = logging.getLogger(__name__)

# Hard limits for crew execution
CREW_TIMEOUT_SECONDS = 120
CREW_FALLBACK_AR = "عذراً، استغرق التحليل وقتاً أطول من المتوقع. يرجى المحاولة مرة أخرى."


class CrewTimeoutError(Exception):
    """Raised when a crew exceeds its execution time limit."""


@contextmanager
def crew_timeout(seconds: int = CREW_TIMEOUT_SECONDS):
    """Context manager that raises CrewTimeoutError after N seconds."""
    def _handler(signum, frame):
        raise CrewTimeoutError(f"Crew exceeded {seconds}s timeout")
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def run_consumer_analysis(*, subscriber_number: str) -> dict:
    """
    Run the consumer analysis crew for a given subscriber.

    Executes sequentially: BillingAgent analyzes bills, AdvisorAgent
    generates savings recommendations, ComplianceAgent checks tariff compliance.

    Args:
        subscriber_number: The consumer's subscriber number.

    Returns:
        Dict with task_results list and raw crew output.
    """
    logger.info("Starting consumer analysis crew for %s", subscriber_number)

    billing_agent = create_billing_agent()
    advisor_agent = create_advisor_agent()
    compliance_agent = create_compliance_agent()

    bill_task = create_bill_analysis_task(
        agent=billing_agent,
        subscriber_number=subscriber_number,
    )
    savings_task = create_savings_recommendation_task(
        agent=advisor_agent,
        subscriber_number=subscriber_number,
    )
    compliance_task = create_compliance_check_task(
        agent=compliance_agent,
        subscriber_number=subscriber_number,
    )

    crew = Crew(
        agents=[billing_agent, advisor_agent, compliance_agent],
        tasks=[bill_task, savings_task, compliance_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        start = time.monotonic()
        with crew_timeout(CREW_TIMEOUT_SECONDS):
            result = crew.kickoff()
        elapsed = int((time.monotonic() - start) * 1000)
        logger.info("Consumer crew completed for %s in %dms", subscriber_number, elapsed)

        return {
            "status": "success",
            "subscriber_number": subscriber_number,
            "raw_output": str(result),
            "elapsed_ms": elapsed,
            "task_results": [
                {"task": "bill_analysis", "output": str(bill_task.output) if bill_task.output else ""},
                {"task": "savings_recommendations", "output": str(savings_task.output) if savings_task.output else ""},
                {"task": "compliance_check", "output": str(compliance_task.output) if compliance_task.output else ""},
            ],
        }

    except CrewTimeoutError:
        logger.error("Consumer crew TIMEOUT for %s after %ds", subscriber_number, CREW_TIMEOUT_SECONDS)
        return {
            "status": "timeout",
            "subscriber_number": subscriber_number,
            "raw_output": CREW_FALLBACK_AR,
            "task_results": [],
        }
    except Exception as e:
        logger.error("Consumer analysis crew failed for %s: %s", subscriber_number, e)
        return {
            "status": "error",
            "subscriber_number": subscriber_number,
            "error": str(e),
            "raw_output": CREW_FALLBACK_AR,
            "task_results": [],
        }


def run_operations_monitoring(*, plant_code: str, turbine_id: int = 0, forecast_hours: int = 24) -> dict:
    """
    Run the operations monitoring crew for a given plant.

    Executes sequentially: MaintenanceAgent diagnoses equipment,
    ForecastAgent analyzes demand, ComplianceAgent checks emissions.

    Args:
        plant_code: The power plant code.
        turbine_id: Optional specific turbine ID to focus on.
        forecast_hours: Number of hours for demand forecast (default: 24).

    Returns:
        Dict with task_results list and raw crew output.
    """
    logger.info("Starting operations monitoring crew for plant %s", plant_code)

    maintenance_agent = create_maintenance_agent()
    forecast_agent = create_forecast_agent()
    compliance_agent = create_compliance_agent()

    maintenance_task = create_maintenance_diagnosis_task(
        agent=maintenance_agent,
        plant_code=plant_code,
        turbine_id=turbine_id,
    )
    forecast_task = create_demand_forecast_task(
        agent=forecast_agent,
        hours=forecast_hours,
    )
    emissions_task = create_emissions_monitoring_task(
        agent=compliance_agent,
        plant_code=plant_code,
    )

    crew = Crew(
        agents=[maintenance_agent, forecast_agent, compliance_agent],
        tasks=[maintenance_task, forecast_task, emissions_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        start = time.monotonic()
        with crew_timeout(CREW_TIMEOUT_SECONDS):
            result = crew.kickoff()
        elapsed = int((time.monotonic() - start) * 1000)
        logger.info("Operations crew completed for plant %s in %dms", plant_code, elapsed)

        return {
            "status": "success",
            "plant_code": plant_code,
            "raw_output": str(result),
            "elapsed_ms": elapsed,
            "task_results": [
                {"task": "maintenance_diagnosis", "output": str(maintenance_task.output) if maintenance_task.output else ""},
                {"task": "demand_forecast", "output": str(forecast_task.output) if forecast_task.output else ""},
                {"task": "emissions_monitoring", "output": str(emissions_task.output) if emissions_task.output else ""},
            ],
        }

    except CrewTimeoutError:
        logger.error("Operations crew TIMEOUT for plant %s after %ds", plant_code, CREW_TIMEOUT_SECONDS)
        return {
            "status": "timeout",
            "plant_code": plant_code,
            "raw_output": CREW_FALLBACK_AR,
            "task_results": [],
        }
    except Exception as e:
        logger.error("Operations monitoring crew failed for plant %s: %s", plant_code, e)
        return {
            "status": "error",
            "plant_code": plant_code,
            "error": str(e),
            "raw_output": CREW_FALLBACK_AR,
            "task_results": [],
        }
