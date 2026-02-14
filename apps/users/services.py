"""
User services - Business logic for user operations.

Services contain business logic and are the main entry point for
creating, updating, and deleting data.
"""
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.core.exceptions import ValidationError

User = get_user_model()


def user_create(
    *,
    email: str,
    password: str,
    username: str = None,
    first_name: str = '',
    last_name: str = '',
    **extra_fields
) -> User:
    """
    Create a new user with the given email and password.

    Raises:
        ValidationError: If email already exists.
    """
    if User.objects.filter(email=email).exists():
        raise ValidationError('User with this email already exists.')

    if username is None:
        username = email.split('@')[0]

    user = User(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        **extra_fields
    )
    user.set_password(password)

    with transaction.atomic():
        user.full_clean()
        user.save()

    return user


def user_update(*, user: User, data: dict) -> User:
    """
    Update user with the given data.

    Only updates fields that are provided in data.
    """
    allowed_fields = ['first_name', 'last_name', 'phone', 'avatar']

    for field, value in data.items():
        if field in allowed_fields:
            setattr(user, field, value)

    with transaction.atomic():
        user.full_clean()
        user.save()

    return user


def user_verify(*, user: User) -> User:
    """Mark user as verified."""
    user.is_verified = True
    user.save(update_fields=['is_verified'])
    return user
