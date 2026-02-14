"""
User selectors - Query logic for retrieving user data.

Selectors contain query logic and are the main entry point for
reading data. They return querysets or model instances.
"""
from django.contrib.auth import get_user_model
from django.db.models import QuerySet

User = get_user_model()


def user_list(*, is_active: bool = True, is_verified: bool = None) -> QuerySet[User]:
    """
    Get a list of users with optional filtering.

    Args:
        is_active: Filter by active status (default: True).
        is_verified: Filter by verification status (optional).

    Returns:
        QuerySet of User objects.
    """
    queryset = User.objects.filter(is_active=is_active)

    if is_verified is not None:
        queryset = queryset.filter(is_verified=is_verified)

    return queryset.order_by('-created_at')


def user_get_by_email(*, email: str) -> User | None:
    """Get a user by email or return None."""
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None


def user_get_by_id(*, user_id: int) -> User | None:
    """Get a user by ID or return None."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None
