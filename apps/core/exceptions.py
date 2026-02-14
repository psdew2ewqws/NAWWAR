"""
Core exceptions - Custom exception classes.
"""
from rest_framework.exceptions import APIException


class ApplicationError(Exception):
    """Base exception for application-level errors."""

    def __init__(self, message: str, extra: dict = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}


class ValidationError(ApplicationError):
    """Raised when validation fails."""
    pass


class NotFoundError(ApplicationError):
    """Raised when a resource is not found."""
    pass


class PermissionDeniedError(ApplicationError):
    """Raised when permission is denied."""
    pass
