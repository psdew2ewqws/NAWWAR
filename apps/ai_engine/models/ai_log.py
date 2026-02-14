"""
AI Engine - AILog model for tracking all AI API calls.
"""
from django.db import models

from apps.core.models.base import TimeStampedModel


class AILog(TimeStampedModel):
    """Tracks every AI provider API call for cost monitoring and debugging."""

    class Provider(models.TextChoices):
        OPENAI = 'openai', 'OpenAI'
        ANTHROPIC = 'anthropic', 'Anthropic'
        LOCAL = 'local', 'Local'

    class TaskType(models.TextChoices):
        VISION = 'vision', 'Vision'
        STT = 'stt', 'Speech-to-Text'
        TTS = 'tts', 'Text-to-Speech'
        RAG = 'rag', 'RAG'
        CHAT = 'chat', 'Chat'
        CREW = 'crew', 'Crew'

    model_name = models.CharField(max_length=100)
    provider = models.CharField(max_length=20, choices=Provider.choices)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ai_log'
        ordering = ['-created_at']
        verbose_name = 'AI Log'
        verbose_name_plural = 'AI Logs'

    def __str__(self):
        return f"{self.provider}:{self.model_name} - {self.task_type} ({self.created_at:%Y-%m-%d %H:%M})"
