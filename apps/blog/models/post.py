"""
Post model for blog posts.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from .category import Category
from .tag import Tag


class Post(TimeStampedModel):
    """Blog Post model with sequential ID and character limits."""

    # Sequential ID field (e.g., POST-001, POST-002)
    seq_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Sequential ID'
    )

    # Title with 100 character limit
    title = models.CharField(
        max_length=100,
        help_text='Maximum 100 characters'
    )

    # Slug with 100 character limit
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='URL-friendly identifier (max 100 characters)'
    )

    # Content field (unlimited)
    content = models.TextField(blank=True)

    # Author reference (One-to-Many: User -> Posts)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )

    # Categories (Many-to-Many: Post <-> Categories)
    categories = models.ManyToManyField(
        Category,
        related_name='posts',
        blank=True
    )

    # Tags (Many-to-Many: Post <-> Tags)
    tags = models.ManyToManyField(
        Tag,
        related_name='posts',
        blank=True
    )

    # Status choices
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )

    class Meta:
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.seq_id} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:100]
        if not self.seq_id:
            self.seq_id = self._generate_seq_id()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_seq_id(cls):
        """Generate sequential ID like POST-001, POST-002, etc."""
        prefix = 'POST'
        last_post = cls.objects.order_by('-id').first()
        if last_post and last_post.seq_id:
            try:
                last_number = int(last_post.seq_id.split('-')[1])
                new_number = last_number + 1
            except (IndexError, ValueError):
                new_number = 1
        else:
            new_number = 1
        return f"{prefix}-{new_number:03d}"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()
