"""
Management command to expire old conversation sessions.

Marks sessions older than SESSION_EXPIRY_DAYS as inactive.
Run via: python manage.py cleanup_sessions [--dry-run]
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.consumer.models import ConversationSession


class Command(BaseCommand):
    help = 'Mark conversation sessions older than SESSION_EXPIRY_DAYS as inactive.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without making changes.',
        )

    def handle(self, *args, **options):
        expiry_days = getattr(settings, 'SESSION_EXPIRY_DAYS', 90)
        cutoff = timezone.now() - timedelta(days=expiry_days)
        dry_run = options['dry_run']

        expired_qs = ConversationSession.objects.filter(
            is_active=True,
            created_at__lt=cutoff,
        )
        count = expired_qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would expire {count} sessions older than {expiry_days} days.'
                )
            )
            return

        updated = expired_qs.update(is_active=False)
        self.stdout.write(
            self.style.SUCCESS(
                f'Expired {updated} sessions older than {expiry_days} days (cutoff: {cutoff.date()}).'
            )
        )
