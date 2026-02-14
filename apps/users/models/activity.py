"""
UserActivity model - Track user actions and audit log.
Demonstrates: Logging, IP address tracking, user agent, audit trail.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class UserActivityManager(models.Manager):
    """Custom manager for UserActivity."""

    def log_activity(self, user, action_type, description, **extra_data):
        """
        Log user activity.

        Usage:
            UserActivity.objects.log_activity(
                user=request.user,
                action_type='login',
                description='User logged in',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        """
        return self.create(
            user=user,
            action_type=action_type,
            description=description,
            **extra_data
        )

    def recent(self, days=7):
        """Get activities from the last N days."""
        from django.utils import timezone
        from datetime import timedelta
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)

    def by_action(self, action_type):
        """Get activities by action type."""
        return self.filter(action_type=action_type)


class UserActivity(TimeStampedModel):
    """
    Log of user activities and actions.
    Useful for audit trails, analytics, and security monitoring.
    """

    # Common action types
    class ActionType(models.TextChoices):
        # Authentication
        LOGIN = 'login', 'Logged In'
        LOGOUT = 'logout', 'Logged Out'
        REGISTER = 'register', 'Registered'
        PASSWORD_CHANGE = 'password_change', 'Changed Password'
        PASSWORD_RESET = 'password_reset', 'Reset Password'

        # Content actions
        POST_CREATE = 'post_create', 'Created Post'
        POST_UPDATE = 'post_update', 'Updated Post'
        POST_DELETE = 'post_delete', 'Deleted Post'
        POST_PUBLISH = 'post_publish', 'Published Post'

        COMMENT_CREATE = 'comment_create', 'Created Comment'
        COMMENT_UPDATE = 'comment_update', 'Updated Comment'
        COMMENT_DELETE = 'comment_delete', 'Deleted Comment'

        # Profile actions
        PROFILE_UPDATE = 'profile_update', 'Updated Profile'
        AVATAR_CHANGE = 'avatar_change', 'Changed Avatar'

        # Social actions
        FOLLOW = 'follow', 'Followed User'
        UNFOLLOW = 'unfollow', 'Unfollowed User'
        LIKE = 'like', 'Liked Post'
        UNLIKE = 'unlike', 'Unliked Post'

        # Admin actions
        ADMIN_ACTION = 'admin_action', 'Admin Action'

        # Generic
        VIEW = 'view', 'Viewed Content'
        DOWNLOAD = 'download', 'Downloaded File'
        OTHER = 'other', 'Other Action'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities',
        help_text='User who performed the action'
    )

    action_type = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        db_index=True,
        help_text='Type of action performed'
    )

    description = models.CharField(
        max_length=255,
        help_text='Brief description of the activity'
    )

    # Additional details (JSON for flexibility)
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional details about the activity (JSON)'
    )

    # Request information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address from where action was performed'
    )

    user_agent = models.TextField(
        blank=True,
        help_text='Browser user agent string'
    )

    # Related object (optional)
    object_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='Type of object affected (e.g., "post", "comment")'
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID of affected object'
    )

    # Success/Failure tracking
    is_successful = models.BooleanField(
        default=True,
        help_text='Was the action successful?'
    )

    error_message = models.TextField(
        blank=True,
        help_text='Error message if action failed'
    )

    # Custom manager
    objects = UserActivityManager()

    class Meta:
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        user_email = self.user.email if self.user else 'Anonymous'
        return f"{user_email} - {self.action_type} at {self.created_at}"

    @property
    def browser_info(self):
        """Extract browser info from user agent."""
        if not self.user_agent:
            return "Unknown"
        # Simple extraction (you can use user-agents library for better parsing)
        if 'Chrome' in self.user_agent:
            return 'Chrome'
        elif 'Firefox' in self.user_agent:
            return 'Firefox'
        elif 'Safari' in self.user_agent:
            return 'Safari'
        elif 'Edge' in self.user_agent:
            return 'Edge'
        return 'Other'

    @classmethod
    def log_login(cls, user, request):
        """Helper to log login activity."""
        return cls.objects.log_activity(
            user=user,
            action_type=cls.ActionType.LOGIN,
            description=f'{user.email} logged in',
            ip_address=cls._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    @classmethod
    def log_logout(cls, user, request):
        """Helper to log logout activity."""
        return cls.objects.log_activity(
            user=user,
            action_type=cls.ActionType.LOGOUT,
            description=f'{user.email} logged out',
            ip_address=cls._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
