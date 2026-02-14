"""
UserProfile model - OneToOne relationship with User.
Demonstrates: OneToOne relationship, JSON field, custom save method, signals.
"""
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import TimeStampedModel


class UserProfile(TimeStampedModel):
    """
    Extended user profile information.
    OneToOne relationship - Each user has exactly one profile.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text='User this profile belongs to'
    )

    # Personal Information
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text='Short biography (max 500 chars)'
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text='User birth date'
    )

    # Contact Information
    website = models.URLField(
        blank=True,
        help_text='Personal website URL'
    )

    github = models.CharField(
        max_length=100,
        blank=True,
        help_text='GitHub username'
    )

    twitter = models.CharField(
        max_length=100,
        blank=True,
        help_text='Twitter handle (without @)'
    )

    linkedin = models.URLField(
        blank=True,
        help_text='LinkedIn profile URL'
    )

    # Location
    country = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    # Preferences - JSON field for flexible data
    preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text='User preferences stored as JSON'
    )

    # Stats
    posts_count = models.PositiveIntegerField(
        default=0,
        help_text='Cached count of user posts'
    )

    followers_count = models.PositiveIntegerField(
        default=0,
        help_text='Cached count of followers'
    )

    # Visibility
    is_public = models.BooleanField(
        default=True,
        help_text='Is this profile visible to others?'
    )

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"Profile of {self.user.email}"

    @property
    def full_location(self):
        """Get formatted location string."""
        if self.city and self.country:
            return f"{self.city}, {self.country}"
        return self.city or self.country or "Not specified"

    @property
    def age(self):
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def get_social_links(self):
        """Get all social media links."""
        links = {}
        if self.github:
            links['github'] = f"https://github.com/{self.github}"
        if self.twitter:
            links['twitter'] = f"https://twitter.com/{self.twitter}"
        if self.linkedin:
            links['linkedin'] = self.linkedin
        if self.website:
            links['website'] = self.website
        return links


# Signal to automatically create profile when user is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved."""
    # Create profile if it doesn't exist
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()
