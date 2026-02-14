"""
AppSettings model - Application-wide settings (Singleton pattern).
Demonstrates: Singleton pattern, admin customization, site configuration.
"""
from django.db import models
from django.core.cache import cache

from .base import TimeStampedModel


class SingletonModel(models.Model):
    """
    Abstract model that ensures only one instance exists.
    Singleton pattern for Django models.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Override save to ensure only one instance exists."""
        self.pk = 1  # Force primary key to always be 1
        super().save(*args, **kwargs)
        # Clear cache when settings are updated
        self.clear_cache()

    def delete(self, *args, **kwargs):
        """Prevent deletion of singleton."""
        pass  # Do nothing - singleton cannot be deleted

    @classmethod
    def load(cls):
        """
        Load the singleton instance.
        Creates it if it doesn't exist.
        """
        # Try to get from cache first
        cache_key = f'{cls.__name__}_singleton'
        obj = cache.get(cache_key)

        if obj is None:
            obj, created = cls.objects.get_or_create(pk=1)
            cache.set(cache_key, obj, 3600)  # Cache for 1 hour

        return obj

    def clear_cache(self):
        """Clear the cached singleton instance."""
        cache_key = f'{self.__class__.__name__}_singleton'
        cache.delete(cache_key)


class AppSettings(SingletonModel, TimeStampedModel):
    """
    Application-wide settings.
    Only one instance can exist (Singleton pattern).

    Usage:
        settings = AppSettings.load()
        print(settings.site_name)
        settings.site_name = "New Name"
        settings.save()
    """

    # Site Information
    site_name = models.CharField(
        max_length=200,
        default='Django Blog',
        help_text='Name of the website'
    )

    site_description = models.TextField(
        default='A professional Django blog platform',
        help_text='Brief description of the site'
    )

    site_logo = models.ImageField(
        upload_to='settings/',
        blank=True,
        null=True,
        help_text='Site logo image'
    )

    # Contact Information
    contact_email = models.EmailField(
        default='admin@example.com',
        help_text='Main contact email'
    )

    support_email = models.EmailField(
        blank=True,
        help_text='Support email address'
    )

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone number'
    )

    # Social Media
    facebook_url = models.URLField(
        blank=True,
        help_text='Facebook page URL'
    )

    twitter_url = models.URLField(
        blank=True,
        help_text='Twitter profile URL'
    )

    instagram_url = models.URLField(
        blank=True,
        help_text='Instagram profile URL'
    )

    linkedin_url = models.URLField(
        blank=True,
        help_text='LinkedIn profile URL'
    )

    github_url = models.URLField(
        blank=True,
        help_text='GitHub organization URL'
    )

    # Feature Flags
    enable_comments = models.BooleanField(
        default=True,
        help_text='Allow comments on blog posts'
    )

    enable_likes = models.BooleanField(
        default=True,
        help_text='Allow users to like posts'
    )

    enable_user_registration = models.BooleanField(
        default=True,
        help_text='Allow new user registration'
    )

    require_email_verification = models.BooleanField(
        default=False,
        help_text='Require email verification for new users'
    )

    maintenance_mode = models.BooleanField(
        default=False,
        help_text='Enable maintenance mode (site will be inaccessible)'
    )

    # Content Settings
    posts_per_page = models.PositiveIntegerField(
        default=10,
        help_text='Number of posts to display per page'
    )

    max_upload_size = models.PositiveIntegerField(
        default=5,  # MB
        help_text='Maximum file upload size in MB'
    )

    allowed_image_formats = models.JSONField(
        default=list,
        blank=True,
        help_text='Allowed image formats (e.g., ["jpg", "png", "gif"])'
    )

    # SEO Settings
    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text='Default meta keywords for SEO'
    )

    meta_description = models.TextField(
        blank=True,
        help_text='Default meta description for SEO'
    )

    google_analytics_id = models.CharField(
        max_length=50,
        blank=True,
        help_text='Google Analytics tracking ID (e.g., UA-XXXXX-Y)'
    )

    # Email Settings
    email_from_name = models.CharField(
        max_length=100,
        default='Django Blog',
        help_text='Name to display in from field of emails'
    )

    smtp_host = models.CharField(
        max_length=255,
        blank=True,
        help_text='SMTP server host'
    )

    smtp_port = models.PositiveIntegerField(
        default=587,
        help_text='SMTP server port'
    )

    # Terms and Privacy
    terms_of_service_url = models.URLField(
        blank=True,
        help_text='URL to terms of service page'
    )

    privacy_policy_url = models.URLField(
        blank=True,
        help_text='URL to privacy policy page'
    )

    # Custom CSS/JS
    custom_css = models.TextField(
        blank=True,
        help_text='Custom CSS to inject into all pages'
    )

    custom_js = models.TextField(
        blank=True,
        help_text='Custom JavaScript to inject into all pages'
    )

    class Meta:
        verbose_name = 'App Settings'
        verbose_name_plural = 'App Settings'

    def __str__(self):
        return f"Settings for {self.site_name}"

    @property
    def social_links(self):
        """Get all social media links."""
        links = {}
        if self.facebook_url:
            links['facebook'] = self.facebook_url
        if self.twitter_url:
            links['twitter'] = self.twitter_url
        if self.instagram_url:
            links['instagram'] = self.instagram_url
        if self.linkedin_url:
            links['linkedin'] = self.linkedin_url
        if self.github_url:
            links['github'] = self.github_url
        return links

    @property
    def is_in_maintenance(self):
        """Check if site is in maintenance mode."""
        return self.maintenance_mode

    def get_allowed_formats(self):
        """Get list of allowed image formats."""
        if not self.allowed_image_formats:
            return ['jpg', 'jpeg', 'png', 'gif', 'webp']
        return self.allowed_image_formats
