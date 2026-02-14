"""
Consumer services - Business logic for consumer operations.

Services contain business logic and are the main entry point for
creating, updating, and deleting data.
"""
from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import ApplicationError, ValidationError
from apps.consumer.models import (
    Subscription,
    Bill,
    BillLineItem,
    Complaint,
    ConversationSession,
    Message,
)


def subscription_create(
    *,
    subscriber_number: str,
    name: str,
    name_ar: str = '',
    phone: str = '',
    email: str = '',
    address: str = '',
    address_ar: str = '',
    district: str = '',
    meter_number: str = '',
    subscription_type: str = Subscription.SubscriptionType.RESIDENTIAL,
) -> Subscription:
    """
    Create a new subscription.

    Raises:
        ValidationError: If subscriber_number already exists.
    """
    if Subscription.objects.filter(subscriber_number=subscriber_number).exists():
        raise ValidationError(f'Subscription with number {subscriber_number} already exists.')

    subscription = Subscription(
        subscriber_number=subscriber_number,
        name=name,
        name_ar=name_ar,
        phone=phone,
        email=email,
        address=address,
        address_ar=address_ar,
        district=district,
        meter_number=meter_number,
        subscription_type=subscription_type,
    )

    with transaction.atomic():
        subscription.full_clean()
        subscription.save()

    return subscription


def bill_create(
    *,
    subscription: Subscription,
    billing_period_start,
    billing_period_end,
    total_amount_fils: int = 0,
    total_kwh: Decimal = Decimal('0'),
    peak_kwh: Decimal = Decimal('0'),
    off_peak_kwh: Decimal = Decimal('0'),
    previous_reading: int = 0,
    current_reading: int = 0,
    due_date,
    is_paid: bool = False,
    scanned_image=None,
    raw_ocr_data: dict = None,
    line_items: list[dict] = None,
) -> Bill:
    """
    Create a new bill with optional line items.

    Args:
        line_items: List of dicts with keys: description, description_ar,
                    amount_fils, kwh, tariff_tier.
    """
    bill = Bill(
        subscription=subscription,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        total_amount_fils=total_amount_fils,
        total_kwh=total_kwh,
        peak_kwh=peak_kwh,
        off_peak_kwh=off_peak_kwh,
        previous_reading=previous_reading,
        current_reading=current_reading,
        due_date=due_date,
        is_paid=is_paid,
        scanned_image=scanned_image,
        raw_ocr_data=raw_ocr_data,
    )

    with transaction.atomic():
        bill.full_clean()
        bill.save()

        if line_items:
            for item in line_items:
                BillLineItem.objects.create(bill=bill, **item)

    return bill


def bill_create_from_scan(
    *,
    subscription: Subscription,
    scan_data: dict,
) -> Bill:
    """
    Create a bill from OCR scan data.

    Expects scan_data to contain:
        billing_period_start, billing_period_end, total_amount_fils,
        total_kwh, peak_kwh, off_peak_kwh, previous_reading,
        current_reading, due_date, line_items (optional list).

    Raises:
        ApplicationError: If required fields are missing from scan_data.
    """
    required_fields = [
        'billing_period_start', 'billing_period_end',
        'total_amount_fils', 'due_date',
    ]
    missing = [f for f in required_fields if f not in scan_data]
    if missing:
        raise ApplicationError(
            f'Scan data missing required fields: {", ".join(missing)}',
            extra={'missing_fields': missing},
        )

    line_items = scan_data.pop('line_items', None)

    return bill_create(
        subscription=subscription,
        raw_ocr_data=scan_data,
        line_items=line_items,
        billing_period_start=scan_data['billing_period_start'],
        billing_period_end=scan_data['billing_period_end'],
        total_amount_fils=scan_data['total_amount_fils'],
        total_kwh=scan_data.get('total_kwh', Decimal('0')),
        peak_kwh=scan_data.get('peak_kwh', Decimal('0')),
        off_peak_kwh=scan_data.get('off_peak_kwh', Decimal('0')),
        previous_reading=scan_data.get('previous_reading', 0),
        current_reading=scan_data.get('current_reading', 0),
        due_date=scan_data['due_date'],
    )


def complaint_create(
    *,
    subscription: Subscription,
    complaint_type: str,
    description: str,
    description_ar: str = '',
) -> Complaint:
    """Create a new complaint for a subscription."""
    complaint = Complaint(
        subscription=subscription,
        complaint_type=complaint_type,
        description=description,
        description_ar=description_ar,
    )

    with transaction.atomic():
        complaint.full_clean()
        complaint.save()

    return complaint


def conversation_create(
    *,
    phone_number: str,
    platform: str = ConversationSession.Platform.WHATSAPP,
    subscription: Subscription = None,
) -> ConversationSession:
    """Create a new conversation session."""
    session = ConversationSession(
        phone_number=phone_number,
        platform=platform,
        subscription=subscription,
    )

    with transaction.atomic():
        session.full_clean()
        session.save()

    return session


def message_create(
    *,
    session: ConversationSession,
    role: str,
    content: str,
    message_type: str = Message.MessageType.TEXT,
    audio_url: str = '',
    image_url: str = '',
    tokens_used: int = 0,
    cost_usd: Decimal = Decimal('0'),
    processing_time_ms: int = 0,
) -> Message:
    """Create a new message in a conversation session."""
    message = Message(
        session=session,
        role=role,
        content=content,
        message_type=message_type,
        audio_url=audio_url,
        image_url=image_url,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        processing_time_ms=processing_time_ms,
    )

    with transaction.atomic():
        message.full_clean()
        message.save()

    return message
