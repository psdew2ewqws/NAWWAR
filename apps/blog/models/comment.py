"""
Comment model for blog posts.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from .post import Post


class Comment(TimeStampedModel):
    """Comment on a blog post with reply support."""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    content = models.TextField()

    # Self-referential for replies (Comment -> Comment)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.post.seq_id}"

    @property
    def is_reply(self):
        return self.parent is not None
