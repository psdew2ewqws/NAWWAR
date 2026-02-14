"""
Conversation models - Chat sessions and messages for the AI assistant.
"""
import string
import secrets

from django.db import models

from apps.core.models import TimeStampedModel


def generate_session_key() -> str:
    """Generate a 12-character random alphanumeric session key."""
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(12))


class ConversationSession(TimeStampedModel):
    """A conversation session between a consumer and the AI assistant."""

    class Platform(models.TextChoices):
        WHATSAPP = 'whatsapp', 'WhatsApp'
        WEB = 'web', 'Web'
        API = 'api', 'API'

    session_key = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        default=generate_session_key,
    )
    subscription = models.ForeignKey(
        'consumer.Subscription',
        on_delete=models.SET_NULL,
        related_name='conversations',
        null=True,
        blank=True,
    )
    phone_number = models.CharField(max_length=20, blank=True, default='')
    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        default=Platform.WHATSAPP,
    )
    is_active = models.BooleanField(default=True)
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Conversation Session'
        verbose_name_plural = 'Conversation Sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f'Session {self.id} - {self.phone_number} ({self.get_platform_display()})'


class Message(TimeStampedModel):
    """A single message within a conversation session."""

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'
        SYSTEM = 'system', 'System'

    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        VOICE = 'voice', 'Voice'
        IMAGE = 'image', 'Image'

    session = models.ForeignKey(
        'consumer.ConversationSession',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    audio_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    processing_time_ms = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_role_display()}: {self.content[:50]}'
