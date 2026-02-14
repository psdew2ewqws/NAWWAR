"""
PostView model - Track post views/analytics.
Demonstrates: Analytics tracking, aggregation, performance optimization.
"""
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from .post import Post


class PostViewManager(models.Manager):
    """Custom manager for PostView."""

    def record_view(self, post, user=None, ip_address=None, user_agent=None):
        """Record a post view."""
        return self.create(
            post=post,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def unique_visitors(self, post):
        """Count unique visitors for a post."""
        return self.filter(post=post).values('ip_address').distinct().count()

    def total_views(self, post):
        """Get total views for a post."""
        return self.filter(post=post).count()

    def views_by_date(self, post):
        """Get views grouped by date."""
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        return (
            self.filter(post=post)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('-date')
        )


class PostView(TimeStampedModel):
    """
    Track views/visits to blog posts.
    Useful for analytics and popular content tracking.
    """

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='views',
        help_text='Post that was viewed'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='post_views',
        help_text='User who viewed the post (if logged in)'
    )

    # Tracking information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of visitor'
    )

    user_agent = models.TextField(
        blank=True,
        help_text='Browser user agent'
    )

    referrer = models.URLField(
        blank=True,
        max_length=500,
        help_text='URL the visitor came from'
    )

    # Session tracking
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Session ID for tracking unique sessions'
    )

    # Duration (optional - requires JavaScript tracking)
    time_spent = models.PositiveIntegerField(
        default=0,
        help_text='Time spent on page in seconds'
    )

    # Custom manager
    objects = PostViewManager()

    class Meta:
        verbose_name = 'Post View'
        verbose_name_plural = 'Post Views'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        viewer = self.user.email if self.user else self.ip_address
        return f"View of {self.post.seq_id} by {viewer}"

    @property
    def is_mobile(self):
        """Check if view was from mobile device."""
        if not self.user_agent:
            return False
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad']
        return any(keyword in self.user_agent.lower() for keyword in mobile_keywords)
