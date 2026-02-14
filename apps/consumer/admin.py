"""
Consumer admin - Register all consumer models.
"""
from django.contrib import admin

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


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['subscriber_number', 'name', 'phone', 'subscription_type', 'is_active', 'created_at']
    list_filter = ['subscription_type', 'is_active', 'district']
    search_fields = ['subscriber_number', 'name', 'name_ar', 'phone', 'email', 'meter_number']


class BillLineItemInline(admin.TabularInline):
    model = BillLineItem
    extra = 0


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'subscription', 'billing_period_start', 'billing_period_end',
        'total_amount_fils', 'total_kwh', 'is_paid', 'due_date',
    ]
    list_filter = ['is_paid', 'billing_period_end']
    search_fields = ['subscription__subscriber_number', 'subscription__name']
    inlines = [BillLineItemInline]


@admin.register(BillLineItem)
class BillLineItemAdmin(admin.ModelAdmin):
    list_display = ['bill', 'description', 'amount_fils', 'kwh', 'tariff_tier']
    list_filter = ['tariff_tier']
    search_fields = ['description', 'description_ar']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscription', 'complaint_type', 'status', 'jepco_reference', 'created_at']
    list_filter = ['complaint_type', 'status']
    search_fields = ['subscription__subscriber_number', 'description', 'jepco_reference']


@admin.register(TariffTier)
class TariffTierAdmin(admin.ModelAdmin):
    list_display = ['sector', 'tier_number', 'min_kwh', 'max_kwh', 'rate_fils', 'is_active']
    list_filter = ['sector', 'is_active']


@admin.register(TariffPeriod)
class TariffPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_hour', 'end_hour', 'multiplier', 'is_peak']
    list_filter = ['is_peak']


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone_number', 'platform', 'subscription', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['phone_number', 'subscription__subscriber_number']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'message_type', 'tokens_used', 'cost_usd', 'created_at']
    list_filter = ['role', 'message_type']
    search_fields = ['content']
