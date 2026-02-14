"""
Consumer selectors - Query logic for retrieving consumer data.

Selectors contain query logic and are the main entry point for
reading data. They return querysets or model instances.
"""
from django.db.models import QuerySet

from apps.consumer.models import (
    Subscription,
    Bill,
    TariffTier,
    TariffPeriod,
    ConversationSession,
    Message,
)


def subscription_get_by_number(*, subscriber_number: str) -> Subscription | None:
    """Get a subscription by subscriber number or return None."""
    try:
        return Subscription.objects.get(subscriber_number=subscriber_number)
    except Subscription.DoesNotExist:
        return None


def subscription_get_by_phone(*, phone: str) -> Subscription | None:
    """Get a subscription by phone number or return None."""
    try:
        return Subscription.objects.get(phone=phone)
    except Subscription.DoesNotExist:
        return None


def bill_list(*, subscription: Subscription, limit: int = 12) -> QuerySet[Bill]:
    """
    Get bills for a subscription, ordered by most recent first.

    Args:
        subscription: The subscription to get bills for.
        limit: Maximum number of bills to return (default: 12).
    """
    return (
        Bill.objects
        .filter(subscription=subscription)
        .select_related('subscription')
        .prefetch_related('line_items')
        .order_by('-billing_period_end')[:limit]
    )


def bill_get_latest(*, subscription: Subscription) -> Bill | None:
    """Get the most recent bill for a subscription."""
    return (
        Bill.objects
        .filter(subscription=subscription)
        .select_related('subscription')
        .prefetch_related('line_items')
        .order_by('-billing_period_end')
        .first()
    )


def tariff_get_active(*, sector: str) -> QuerySet[TariffTier]:
    """Get active tariff tiers for a given sector."""
    return (
        TariffTier.objects
        .filter(sector=sector, is_active=True)
        .order_by('tier_number')
    )


def tariff_periods_list() -> QuerySet[TariffPeriod]:
    """Get all tariff periods."""
    return TariffPeriod.objects.all().order_by('start_hour')


def conversation_get_active(*, phone_number: str) -> ConversationSession | None:
    """Get the active conversation session for a phone number."""
    return (
        ConversationSession.objects
        .filter(phone_number=phone_number, is_active=True)
        .order_by('-created_at')
        .first()
    )


def message_list(*, session: ConversationSession, limit: int = 50) -> QuerySet[Message]:
    """
    Get messages for a conversation session, ordered chronologically.

    Args:
        session: The conversation session.
        limit: Maximum number of messages to return (default: 50).
    """
    return (
        Message.objects
        .filter(session=session)
        .order_by('created_at')[:limit]
    )
