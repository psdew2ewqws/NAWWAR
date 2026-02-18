"""
Vision service — bill scanning and image analysis.

Orchestrates the OpenAI vision client with prompt templates and
output validation to extract structured data from electricity bill images.
"""
import json
import logging

from apps.ai_engine.clients.openai_client import OpenAIClient
from apps.ai_engine.prompts.bill_scanner import BILL_EXTRACTION_PROMPT, BILL_ANALYSIS_PROMPT
from apps.ai_engine.validators.output_validator import validate_bill_scan, validate_ai_response

logger = logging.getLogger(__name__)


async def scan_bill(*, image_data: bytes, mime_type: str = 'image/jpeg') -> dict:
    """
    Extract structured billing data from an electricity bill image.

    Sends the image to GPT-4o vision with the BILL_EXTRACTION_PROMPT,
    validates the returned JSON, and returns cleaned bill data.

    Args:
        image_data: Raw image bytes (JPEG or PNG).
        mime_type: MIME type of the image (default: image/jpeg).

    Returns:
        Validated dict with fields:
            account_number, billing_period_start, billing_period_end,
            consumption_kwh, total_amount_fils, total_amount_jod,
            previous_reading, current_reading, tier_breakdown, etc.

    Raises:
        ValueError: If the extracted data fails validation.
        Exception: If the OpenAI API call fails.
    """
    client = OpenAIClient()

    logger.info("Starting bill scan (image size: %d bytes, type: %s)", len(image_data), mime_type)

    raw_data = await client.vision_extract(
        image_data=image_data,
        prompt=BILL_EXTRACTION_PROMPT,
    )

    validated = validate_bill_scan(raw_data)

    # Map OCR fields to the internal Bill model schema
    result = {
        'subscriber_number': validated.get('account_number'),
        'billing_period_start': validated.get('billing_period_start'),
        'billing_period_end': validated.get('billing_period_end'),
        'total_amount_fils': validated.get('total_amount_fils', 0),
        'total_kwh': validated.get('consumption_kwh', 0),
        'peak_kwh': 0,
        'off_peak_kwh': 0,
        'previous_reading': validated.get('previous_reading', 0),
        'current_reading': validated.get('current_reading', 0),
        'due_date': validated.get('due_date'),
        'line_items': _build_line_items(validated.get('tier_breakdown', [])),
        'raw_ocr': validated,
    }

    logger.info(
        "Bill scan complete: account=%s, consumption=%s kWh, total=%s fils",
        result['subscriber_number'],
        result['total_kwh'],
        result['total_amount_fils'],
    )

    return result


async def analyze_bill(*, bill_data: dict) -> dict:
    """
    Analyze extracted bill data and return consumer-facing insights.

    Args:
        bill_data: Dict of bill fields (from scan_bill or database).

    Returns:
        Dict with summary_ar, consumption_assessment, tier_analysis_ar,
        savings_tips_ar, etc.
    """
    client = OpenAIClient()

    prompt = BILL_ANALYSIS_PROMPT.format(bill_data=json.dumps(bill_data, ensure_ascii=False, default=str))

    raw = await client.vision_extract(
        image_data=b'',  # No image needed — text-only analysis
        prompt=prompt,
    )

    return raw


def _build_line_items(tier_breakdown: list) -> list[dict]:
    """Convert OCR tier_breakdown to BillLineItem-compatible dicts."""
    if not tier_breakdown:
        return []

    items = []
    for tier in tier_breakdown:
        tier_num = tier.get('tier', 0)
        kwh = tier.get('kwh', 0)
        rate = tier.get('rate_fils', 0)
        amount = tier.get('amount_fils', 0)

        items.append({
            'description': f'Tier {tier_num}: {kwh} kWh @ {rate} fils/kWh',
            'description_ar': f'الشريحة {tier_num}: {kwh} ك.و.س × {rate/1000:.3f} دينار',
            'amount_fils': amount,
            'kwh': kwh,
            'tariff_tier': tier_num,
        })

    return items
