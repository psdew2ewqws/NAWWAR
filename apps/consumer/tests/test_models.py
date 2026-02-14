"""
Tests for consumer app models.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.consumer.models import (
    Subscription,
    Bill,
    BillLineItem,
    Complaint,
    ConversationSession,
    Message,
    TariffTier,
    TariffPeriod,
)


class SubscriptionModelTest(TestCase):
    """Tests for the Subscription model."""

    def setUp(self):
        self.subscription = Subscription.objects.create(
            subscriber_number='1001234',
            name='Ahmad Al-Jordani',
            name_ar='أحمد الأردني',
            phone='+962791234567',
            email='ahmad@example.com',
            subscription_type=Subscription.SubscriptionType.RESIDENTIAL,
        )

    def test_subscription_creation(self):
        self.assertEqual(self.subscription.subscriber_number, '1001234')
        self.assertEqual(self.subscription.name, 'Ahmad Al-Jordani')
        self.assertTrue(self.subscription.is_active)

    def test_subscription_str(self):
        self.assertEqual(str(self.subscription), '1001234 - Ahmad Al-Jordani')

    def test_subscription_default_type(self):
        sub = Subscription.objects.create(
            subscriber_number='1001235',
            name='Test User',
        )
        self.assertEqual(sub.subscription_type, 'residential')

    def test_subscription_type_choices(self):
        self.assertIn(('residential', 'Residential'), Subscription.SubscriptionType.choices)
        self.assertIn(('commercial', 'Commercial'), Subscription.SubscriptionType.choices)
        self.assertIn(('industrial', 'Industrial'), Subscription.SubscriptionType.choices)

    def test_subscription_unique_number(self):
        with self.assertRaises(Exception):
            Subscription.objects.create(
                subscriber_number='1001234',
                name='Duplicate',
            )

    def test_subscription_timestamps(self):
        self.assertIsNotNone(self.subscription.created_at)
        self.assertIsNotNone(self.subscription.updated_at)


class BillModelTest(TestCase):
    """Tests for Bill and BillLineItem models."""

    def setUp(self):
        self.subscription = Subscription.objects.create(
            subscriber_number='2001234',
            name='Sara Al-Masri',
        )
        self.bill = Bill.objects.create(
            subscription=self.subscription,
            billing_period_start=date(2024, 1, 1),
            billing_period_end=date(2024, 1, 31),
            total_amount_fils=15000,
            total_kwh=Decimal('350.00'),
            due_date=date(2024, 2, 15),
        )

    def test_bill_creation(self):
        self.assertEqual(self.bill.subscription, self.subscription)
        self.assertEqual(self.bill.total_amount_fils, 15000)
        self.assertEqual(self.bill.total_kwh, Decimal('350.00'))

    def test_bill_str(self):
        self.assertIn('2001234', str(self.bill))

    def test_bill_default_not_paid(self):
        self.assertFalse(self.bill.is_paid)

    def test_bill_with_line_items(self):
        item1 = BillLineItem.objects.create(
            bill=self.bill,
            description='Tier 1 (0-160 kWh)',
            amount_fils=5280,
            kwh=Decimal('160.00'),
            tariff_tier='Tier 1',
        )
        item2 = BillLineItem.objects.create(
            bill=self.bill,
            description='Tier 2 (161-300 kWh)',
            amount_fils=7140,
            kwh=Decimal('140.00'),
            tariff_tier='Tier 2',
        )
        self.assertEqual(self.bill.line_items.count(), 2)
        self.assertIn(item1, self.bill.line_items.all())
        self.assertIn(item2, self.bill.line_items.all())

    def test_bill_line_item_str(self):
        item = BillLineItem.objects.create(
            bill=self.bill,
            description='Fuel surcharge',
            amount_fils=2500,
        )
        self.assertEqual(str(item), 'Fuel surcharge - 2500 fils')

    def test_bill_relationship_to_subscription(self):
        self.assertIn(self.bill, self.subscription.bills.all())


class ComplaintModelTest(TestCase):
    """Tests for the Complaint model."""

    def setUp(self):
        self.subscription = Subscription.objects.create(
            subscriber_number='3001234',
            name='Mohammed Ali',
        )
        self.complaint = Complaint.objects.create(
            subscription=self.subscription,
            complaint_type=Complaint.ComplaintType.OUTAGE,
            description='Power outage in Abdoun area since 2 hours.',
        )

    def test_complaint_creation(self):
        self.assertEqual(self.complaint.subscription, self.subscription)
        self.assertEqual(self.complaint.complaint_type, 'outage')
        self.assertIn('Abdoun', self.complaint.description)

    def test_complaint_default_status(self):
        self.assertEqual(self.complaint.status, Complaint.Status.OPEN)

    def test_complaint_str(self):
        result = str(self.complaint)
        self.assertIn('Power Outage', result)
        self.assertIn('3001234', result)

    def test_complaint_status_transition(self):
        self.complaint.status = Complaint.Status.IN_PROGRESS
        self.complaint.save()
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'in_progress')

        self.complaint.status = Complaint.Status.RESOLVED
        self.complaint.resolution_notes = 'Transformer replaced.'
        self.complaint.save()
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'resolved')
        self.assertEqual(self.complaint.resolution_notes, 'Transformer replaced.')

    def test_complaint_type_choices(self):
        self.assertIn(('outage', 'Power Outage'), Complaint.ComplaintType.choices)
        self.assertIn(('billing', 'Billing Issue'), Complaint.ComplaintType.choices)
        self.assertIn(('meter', 'Meter Problem'), Complaint.ComplaintType.choices)
        self.assertIn(('voltage', 'Voltage Issue'), Complaint.ComplaintType.choices)

    def test_complaint_status_choices(self):
        self.assertIn(('open', 'Open'), Complaint.Status.choices)
        self.assertIn(('in_progress', 'In Progress'), Complaint.Status.choices)
        self.assertIn(('resolved', 'Resolved'), Complaint.Status.choices)
        self.assertIn(('closed', 'Closed'), Complaint.Status.choices)


class ConversationModelTest(TestCase):
    """Tests for ConversationSession and Message models."""

    def setUp(self):
        self.subscription = Subscription.objects.create(
            subscriber_number='4001234',
            name='Fatima Hassan',
        )
        self.session = ConversationSession.objects.create(
            subscription=self.subscription,
            phone_number='+962791112222',
            platform=ConversationSession.Platform.WHATSAPP,
        )

    def test_session_creation(self):
        self.assertEqual(self.session.phone_number, '+962791112222')
        self.assertEqual(self.session.platform, 'whatsapp')
        self.assertTrue(self.session.is_active)

    def test_session_str(self):
        result = str(self.session)
        self.assertIn('+962791112222', result)
        self.assertIn('WhatsApp', result)

    def test_session_default_context(self):
        self.assertEqual(self.session.context, {})

    def test_session_nullable_subscription(self):
        anon_session = ConversationSession.objects.create(
            phone_number='+962790001111',
            platform=ConversationSession.Platform.WEB,
        )
        self.assertIsNone(anon_session.subscription)

    def test_message_creation(self):
        msg = Message.objects.create(
            session=self.session,
            role=Message.Role.USER,
            content='I want to check my bill.',
        )
        self.assertEqual(msg.session, self.session)
        self.assertEqual(msg.role, 'user')
        self.assertEqual(msg.content, 'I want to check my bill.')

    def test_message_str(self):
        msg = Message.objects.create(
            session=self.session,
            role=Message.Role.ASSISTANT,
            content='Sure, let me look up your account.',
        )
        result = str(msg)
        self.assertIn('Assistant', result)
        self.assertIn('Sure, let me look up', result)

    def test_message_default_type(self):
        msg = Message.objects.create(
            session=self.session,
            role=Message.Role.USER,
            content='Hello',
        )
        self.assertEqual(msg.message_type, 'text')

    def test_message_defaults(self):
        msg = Message.objects.create(
            session=self.session,
            role=Message.Role.USER,
            content='Test',
        )
        self.assertEqual(msg.tokens_used, 0)
        self.assertEqual(msg.cost_usd, Decimal('0'))
        self.assertEqual(msg.processing_time_ms, 0)

    def test_conversation_messages_relationship(self):
        Message.objects.create(
            session=self.session,
            role=Message.Role.USER,
            content='Hi',
        )
        Message.objects.create(
            session=self.session,
            role=Message.Role.ASSISTANT,
            content='Hello!',
        )
        self.assertEqual(self.session.messages.count(), 2)

    def test_platform_choices(self):
        self.assertIn(('whatsapp', 'WhatsApp'), ConversationSession.Platform.choices)
        self.assertIn(('web', 'Web'), ConversationSession.Platform.choices)
        self.assertIn(('api', 'API'), ConversationSession.Platform.choices)


class TariffModelTest(TestCase):
    """Tests for TariffTier and TariffPeriod models."""

    def test_tariff_tier_creation(self):
        tier = TariffTier.objects.create(
            sector=TariffTier.Sector.RESIDENTIAL,
            tier_number=1,
            min_kwh=0,
            max_kwh=160,
            rate_fils=33,
        )
        self.assertEqual(tier.sector, 'residential')
        self.assertEqual(tier.rate_fils, 33)
        self.assertTrue(tier.is_active)

    def test_tariff_tier_str(self):
        tier = TariffTier.objects.create(
            sector=TariffTier.Sector.COMMERCIAL,
            tier_number=2,
            min_kwh=500,
            max_kwh=1000,
            rate_fils=72,
        )
        result = str(tier)
        self.assertIn('Commercial', result)
        self.assertIn('Tier 2', result)
        self.assertIn('72', result)

    def test_tariff_period_creation(self):
        period = TariffPeriod.objects.create(
            name='Peak',
            start_hour=12,
            end_hour=18,
            multiplier=Decimal('1.50'),
            is_peak=True,
        )
        self.assertEqual(period.name, 'Peak')
        self.assertTrue(period.is_peak)
        self.assertEqual(period.multiplier, Decimal('1.50'))

    def test_tariff_period_str(self):
        period = TariffPeriod.objects.create(
            name='Off-Peak',
            start_hour=22,
            end_hour=6,
            multiplier=Decimal('0.75'),
            is_peak=False,
        )
        result = str(period)
        self.assertIn('Off-Peak', result)
        self.assertIn('22:00', result)
        self.assertIn('6:00', result)
