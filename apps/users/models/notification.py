"""
Notification model - User notifications system.
Demonstrates: Choices, custom managers, bulk operations, filtering.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class NotificationManager(models.Manager):
    """Custom manager for Notification model."""

    def unread(self):
        """Get all unread notifications."""
        return self.filter(is_read=False)

    def read(self):
        """Get all read notifications."""
        return self.filter(is_read=True)

    def for_user(self, user):
        """Get all notifications for a specific user."""
        return self.filter(user=user)

    def mark_all_as_read(self, user):
        """Mark all notifications as read for a user."""
        return self.filter(user=user, is_read=False).update(is_read=True)


class Notification(TimeStampedModel):
    """
    User notifications.
    Demonstrates: Custom managers, choices, database indexes.
    """

    # Notification types
    class NotificationType(models.TextChoices):
        INFO = 'info', 'Information'
        SUCCESS = 'success', 'Success'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        COMMENT = 'comment', 'New Comment'
        LIKE = 'like', 'New Like'
        MENTION = 'mention', 'Mentioned You'
        FOLLOW = 'follow', 'New Follower'
        SYSTEM = 'system', 'System Notification'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='User who receives this notification'
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        help_text='Type of notification'
    )

    title = models.CharField(
        max_length=200,
        help_text='Notification title'
    )

    message = models.TextField(
        help_text='Notification message content'
    )

    # Link to related object (optional)
    link = models.URLField(
        blank=True,
        help_text='URL to navigate when notification is clicked'
    )

    # Related object tracking (Generic approach)
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='Type of related object (e.g., "post", "comment")'
    )

    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID of related object'
    )

    # Status
    is_read = models.BooleanField(
        default=False,
        help_text='Has user read this notification?',
        db_index=True  # Index for faster queries
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When was this notification read?'
    )

    # Priority
    is_important = models.BooleanField(
        default=False,
        help_text='Is this an important notification?'
    )

    # Custom manager
    objects = NotificationManager()

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.title} for {self.user.email}"

    def mark_as_read(self):
        """Mark this notification as read."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        """Mark this notification as unread."""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def send_notification(cls, user, notification_type, title, message, **kwargs):
        """
        Helper method to create a notification.

        Usage:
            Notification.send_notification(
                user=user,
                notification_type='comment',
                title='New Comment',
                message='Someone commented on your post',
                link='/posts/123/',
                is_important=True
            )
        """
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
