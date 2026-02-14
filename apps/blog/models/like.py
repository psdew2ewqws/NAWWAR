"""
Like model for blog posts.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from .post import Post


class Like(TimeStampedModel):
    """Like on a blog post (unique per user per post)."""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    class Meta:
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'
        # Ensure one like per user per post
        unique_together = ['post', 'user']

    def __str__(self):
        return f"{self.user} likes {self.post.seq_id}"
