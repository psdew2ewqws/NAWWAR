"""
Management command to seed EMRC tariff data.

Populates TariffTier from settings.EMRC_TARIFFS and creates TariffPeriod entries.
"""
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.consumer.models import TariffTier, TariffPeriod


TARIFF_PERIODS = [
    {
        'name': 'Off-Peak',
        'name_ar': 'خارج الذروة',
        'start_hour': 21,
        'end_hour': 8,
        'multiplier': Decimal('0.80'),
        'is_peak': False,
    },
    {
        'name': 'Shoulder (Morning)',
        'name_ar': 'شبه ذروة (صباحاً)',
        'start_hour': 8,
        'end_hour': 13,
        'multiplier': Decimal('1.20'),
        'is_peak': False,
    },
    {
        'name': 'Peak',
        'name_ar': 'ذروة',
        'start_hour': 13,
        'end_hour': 17,
        'multiplier': Decimal('1.50'),
        'is_peak': True,
    },
    {
        'name': 'Shoulder (Evening)',
        'name_ar': 'شبه ذروة (مساءً)',
        'start_hour': 17,
        'end_hour': 21,
        'multiplier': Decimal('1.20'),
        'is_peak': False,
    },
]


class Command(BaseCommand):
    help = 'Seed EMRC tariff tiers and time-of-use periods.'

    def handle(self, *args, **options):
        self._seed_tariff_tiers()
        self._seed_tariff_periods()
        self.stdout.write(self.style.SUCCESS('Tariff data seeded successfully!'))

    def _seed_tariff_tiers(self):
        self.stdout.write('Seeding tariff tiers...')
        count = 0
        for sector, tiers in settings.EMRC_TARIFFS.items():
            for tier_data in tiers:
                # Skip time-of-use entries that lack min/max_kwh
                if 'min_kwh' not in tier_data or 'max_kwh' not in tier_data:
                    continue
                _, created = TariffTier.objects.update_or_create(
                    sector=sector.lower(),
                    tier_number=tier_data['tier'],
                    defaults={
                        'min_kwh': tier_data['min_kwh'],
                        'max_kwh': tier_data['max_kwh'],
                        'rate_fils': tier_data['rate_fils'],
                        'is_active': True,
                    },
                )
                if created:
                    count += 1
        self.stdout.write(f'  Created {count} tariff tiers (total: {TariffTier.objects.count()})')

    def _seed_tariff_periods(self):
        self.stdout.write('Seeding tariff periods...')
        count = 0
        for period_data in TARIFF_PERIODS:
            _, created = TariffPeriod.objects.update_or_create(
                name=period_data['name'],
                defaults=period_data,
            )
            if created:
                count += 1
        self.stdout.write(f'  Created {count} tariff periods (total: {TariffPeriod.objects.count()})')
