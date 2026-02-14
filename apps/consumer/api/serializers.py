"""
Consumer API serializers.
"""
from rest_framework import serializers

from apps.consumer.models import (
    Subscription,
    Bill,
    BillLineItem,
    Complaint,
    TariffTier,
    TariffPeriod,
    ConversationSession,
    Message,
)


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model (read-only)."""

    class Meta:
        model = Subscription
        fields = [
            'id', 'subscriber_number', 'name', 'name_ar', 'phone', 'email',
            'address', 'address_ar', 'district', 'meter_number',
            'subscription_type', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating a subscription."""

    subscriber_number = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=255)
    name_ar = serializers.CharField(max_length=255, required=False, default='')
    phone = serializers.CharField(max_length=20, required=False, default='')
    email = serializers.EmailField(required=False, default='')
    address = serializers.CharField(required=False, default='')
    address_ar = serializers.CharField(required=False, default='')
    district = serializers.CharField(max_length=100, required=False, default='')
    meter_number = serializers.CharField(max_length=50, required=False, default='')
    subscription_type = serializers.ChoiceField(
        choices=Subscription.SubscriptionType.choices,
        default=Subscription.SubscriptionType.RESIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Bill
# ---------------------------------------------------------------------------

class BillLineItemSerializer(serializers.ModelSerializer):
    """Serializer for BillLineItem model (read-only)."""

    class Meta:
        model = BillLineItem
        fields = ['id', 'description', 'description_ar', 'amount_fils', 'kwh', 'tariff_tier']
        read_only_fields = ['id']


class BillSerializer(serializers.ModelSerializer):
    """Serializer for Bill model (read-only)."""

    line_items = BillLineItemSerializer(many=True, read_only=True)
    subscriber_number = serializers.CharField(source='subscription.subscriber_number', read_only=True)

    class Meta:
        model = Bill
        fields = [
            'id', 'subscriber_number', 'billing_period_start', 'billing_period_end',
            'total_amount_fils', 'total_kwh', 'peak_kwh', 'off_peak_kwh',
            'previous_reading', 'current_reading', 'due_date', 'is_paid',
            'scanned_image', 'raw_ocr_data', 'line_items', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class BillCreateSerializer(serializers.Serializer):
    """Serializer for creating a bill."""

    subscriber_number = serializers.CharField(max_length=20)
    billing_period_start = serializers.DateField()
    billing_period_end = serializers.DateField()
    total_amount_fils = serializers.IntegerField(default=0)
    total_kwh = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    peak_kwh = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    off_peak_kwh = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    previous_reading = serializers.IntegerField(default=0)
    current_reading = serializers.IntegerField(default=0)
    due_date = serializers.DateField()
    is_paid = serializers.BooleanField(default=False)


class BillScanSerializer(serializers.Serializer):
    """Serializer for creating a bill from scan data."""

    subscriber_number = serializers.CharField(max_length=20)
    scan_data = serializers.DictField()


# ---------------------------------------------------------------------------
# Complaint
# ---------------------------------------------------------------------------

class ComplaintSerializer(serializers.ModelSerializer):
    """Serializer for Complaint model (read-only)."""

    subscriber_number = serializers.CharField(source='subscription.subscriber_number', read_only=True)

    class Meta:
        model = Complaint
        fields = [
            'id', 'subscriber_number', 'complaint_type', 'description',
            'description_ar', 'status', 'jepco_reference', 'resolution_notes',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'jepco_reference', 'resolution_notes', 'created_at']


class ComplaintCreateSerializer(serializers.Serializer):
    """Serializer for creating a complaint."""

    subscriber_number = serializers.CharField(max_length=20)
    complaint_type = serializers.ChoiceField(choices=Complaint.ComplaintType.choices)
    description = serializers.CharField()
    description_ar = serializers.CharField(required=False, default='')


# ---------------------------------------------------------------------------
# Tariff
# ---------------------------------------------------------------------------

class TariffTierSerializer(serializers.ModelSerializer):
    """Serializer for TariffTier model (read-only)."""

    class Meta:
        model = TariffTier
        fields = ['id', 'sector', 'tier_number', 'min_kwh', 'max_kwh', 'rate_fils', 'is_active']
        read_only_fields = ['id']


class TariffPeriodSerializer(serializers.ModelSerializer):
    """Serializer for TariffPeriod model (read-only)."""

    class Meta:
        model = TariffPeriod
        fields = ['id', 'name', 'name_ar', 'start_hour', 'end_hour', 'multiplier', 'is_peak']
        read_only_fields = ['id']


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class ConversationSessionSerializer(serializers.ModelSerializer):
    """Serializer for ConversationSession model (read-only)."""

    subscriber_number = serializers.CharField(
        source='subscription.subscriber_number', read_only=True, default=None,
    )

    class Meta:
        model = ConversationSession
        fields = [
            'id', 'subscriber_number', 'phone_number', 'platform',
            'is_active', 'context', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating a conversation session."""

    phone_number = serializers.CharField(max_length=20)
    platform = serializers.ChoiceField(
        choices=ConversationSession.Platform.choices,
        default=ConversationSession.Platform.WHATSAPP,
    )


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model (read-only)."""

    class Meta:
        model = Message
        fields = [
            'id', 'session', 'role', 'content', 'message_type',
            'audio_url', 'image_url', 'tokens_used', 'cost_usd',
            'processing_time_ms', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating a message."""

    session_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=Message.Role.choices)
    content = serializers.CharField()
    message_type = serializers.ChoiceField(
        choices=Message.MessageType.choices,
        default=Message.MessageType.TEXT,
    )
    audio_url = serializers.URLField(required=False, default='')
    image_url = serializers.URLField(required=False, default='')


# ---------------------------------------------------------------------------
# AI-powered endpoints
# ---------------------------------------------------------------------------

class BillImageScanSerializer(serializers.Serializer):
    """Serializer for bill image upload and AI scanning."""

    image = serializers.ImageField(help_text='Bill image (JPEG/PNG)')
    subscriber_number = serializers.CharField(
        max_length=20,
        required=False,
        default='',
        help_text='Optional: link the scan result to this subscription.',
    )


class BillAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for requesting AI analysis of an existing bill."""

    bill_id = serializers.IntegerField(help_text='ID of the bill to analyze.')


class ConsumerQuerySerializer(serializers.Serializer):
    """Serializer for consumer RAG query."""

    query = serializers.CharField(help_text='Question in Arabic or English.')
    language = serializers.ChoiceField(
        choices=[('ar', 'Arabic'), ('en', 'English')],
        default='ar',
    )


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

class VoiceQuerySerializer(serializers.Serializer):
    """Serializer for voice query input (audio file upload)."""

    audio = serializers.FileField(help_text='Audio file (OGG/WAV/MP3) to transcribe and process.')


class VoiceResponseSerializer(serializers.Serializer):
    """Serializer for voice query response (read-only)."""

    transcript = serializers.CharField()
    response_text = serializers.CharField()
    intent = serializers.CharField()
    audio_url = serializers.CharField(allow_blank=True, default='')


# ---------------------------------------------------------------------------
# Savings
# ---------------------------------------------------------------------------

class SavingsAnalysisSerializer(serializers.Serializer):
    """Serializer for savings analysis input."""

    subscription_id = serializers.IntegerField(help_text='ID of the Subscription to analyze.')


class SavingsRecommendationSerializer(serializers.Serializer):
    """Serializer for a single savings recommendation."""

    type = serializers.CharField()
    title = serializers.CharField()
    title_ar = serializers.CharField()
    description = serializers.CharField()
    description_ar = serializers.CharField()
    potential_savings_fils = serializers.IntegerField()


class SavingsResultSerializer(serializers.Serializer):
    """Serializer for savings calculation result."""

    current_monthly_cost_fils = serializers.IntegerField()
    optimized_monthly_cost_fils = serializers.IntegerField()
    savings_fils = serializers.IntegerField()
    savings_jod = serializers.FloatField()
    savings_percent = serializers.FloatField()
    recommendations = SavingsRecommendationSerializer(many=True)


class ConsumptionProfileSerializer(serializers.Serializer):
    """Serializer for consumption profile."""

    subscription_id = serializers.IntegerField()
    subscriber_number = serializers.CharField()
    subscription_type = serializers.CharField()
    bills_analyzed = serializers.IntegerField()
    total_kwh = serializers.FloatField()
    avg_monthly_kwh = serializers.FloatField()
    avg_daily_kwh = serializers.FloatField()
    peak_kwh = serializers.FloatField()
    off_peak_kwh = serializers.FloatField()
    peak_ratio = serializers.FloatField()
    billing_days = serializers.IntegerField()
    avg_amount_fils = serializers.IntegerField()
    current_tier = serializers.IntegerField()


class SavingsResponseSerializer(serializers.Serializer):
    """Serializer for the full savings analysis response."""

    consumption_profile = ConsumptionProfileSerializer()
    savings = SavingsResultSerializer()
    ai_recommendations = serializers.CharField()
