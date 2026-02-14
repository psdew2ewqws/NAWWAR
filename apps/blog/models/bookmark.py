"""
Bookmark model - Users can bookmark posts.
Demonstrates: Unique together, compound indexes, user favorites.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from .post import Post


class BookmarkManager(models.Manager):
    """Custom manager for Bookmark."""

    def for_user(self, user):
        """Get all bookmarks for a user."""
        return self.filter(user=user).select_related('post', 'post__author')

    def is_bookmarked(self, user, post):
        """Check if user has bookmarked a post."""
        return self.filter(user=user, post=post).exists()

    def toggle_bookmark(self, user, post):
        """
        Toggle bookmark - add if doesn't exist, remove if exists.
        Returns (bookmark, created) tuple.
        """
        bookmark, created = self.get_or_create(user=user, post=post)
        if not created:
            bookmark.delete()
            return None, False
        return bookmark, True


class Bookmark(TimeStampedModel):
    """
    User bookmarks/favorites for posts.
    Allows users to save posts for later reading.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        help_text='User who bookmarked the post'
    )

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        help_text='Post that was bookmarked'
    )

    # Optional: Add notes or tags to bookmarks
    notes = models.TextField(
        blank=True,
        help_text='Personal notes about this bookmark'
    )

    # Optional: Organize bookmarks into folders/collections
    collection = models.CharField(
        max_length=100,
        blank=True,
        help_text='Collection/folder name for organization'
    )

    # Custom manager
    objects = BookmarkManager()

    class Meta:
        verbose_name = 'Bookmark'
        verbose_name_plural = 'Bookmarks'
        ordering = ['-created_at']
        # Ensure one bookmark per user per post
        unique_together = ['user', 'post']
        # Compound index for faster queries
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'collection']),
        ]

    def __str__(self):
        return f"{self.user.email} bookmarked {self.post.seq_id}"
