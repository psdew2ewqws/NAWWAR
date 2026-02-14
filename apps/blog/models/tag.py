"""
Tag model for blog posts.
"""
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Tag(TimeStampedModel):
    """Tag for labeling blog posts."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:50]
        super().save(*args, **kwargs)
