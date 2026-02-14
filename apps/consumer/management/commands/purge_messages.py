"""
Management command to delete old messages beyond the retention period.

Deletes Message records older than MESSAGE_RETENTION_DAYS.
Session metadata is preserved.
Run via: python manage.py purge_messages [--dry-run]
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.consumer.models import Message


class Command(BaseCommand):
    help = 'Delete messages older than MESSAGE_RETENTION_DAYS.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without making changes.',
        )

    def handle(self, *args, **options):
        retention_days = getattr(settings, 'MESSAGE_RETENTION_DAYS', 180)
        cutoff = timezone.now() - timedelta(days=retention_days)
        dry_run = options['dry_run']

        old_messages = Message.objects.filter(created_at__lt=cutoff)
        count = old_messages.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would delete {count} messages older than {retention_days} days.'
                )
            )
            return

        deleted, _ = old_messages.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f'Purged {deleted} messages older than {retention_days} days (cutoff: {cutoff.date()}).'
            )
        )
