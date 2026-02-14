"""
Consumer API URLs.
"""
from django.urls import path

from apps.consumer.api import views

urlpatterns = [
    # Subscriptions
    path('subscriptions/', views.SubscriptionCreateApi.as_view(), name='subscription-create'),
    path('subscriptions/<str:subscriber_number>/', views.SubscriptionDetailApi.as_view(), name='subscription-detail'),

    # Bills
    path('subscriptions/<str:subscriber_number>/bills/', views.BillListApi.as_view(), name='bill-list'),
    path('bills/', views.BillCreateApi.as_view(), name='bill-create'),
    path('bills/scan/', views.BillScanApi.as_view(), name='bill-scan'),

    # Complaints
    path('complaints/', views.ComplaintCreateApi.as_view(), name='complaint-create'),

    # Tariffs
    path('tariffs/tiers/', views.TariffTierListApi.as_view(), name='tariff-tier-list'),
    path('tariffs/periods/', views.TariffPeriodListApi.as_view(), name='tariff-period-list'),

    # Conversations
    path('conversations/', views.ConversationCreateApi.as_view(), name='conversation-create'),
    path('conversations/<str:phone_number>/', views.ConversationDetailApi.as_view(), name='conversation-detail'),

    # Messages
    path('conversations/<int:session_id>/messages/', views.MessageListApi.as_view(), name='message-list'),
    path('messages/', views.MessageCreateApi.as_view(), name='message-create'),

    # AI-powered
    path('bills/image-scan/', views.BillImageScanApi.as_view(), name='bill-image-scan'),
    path('bills/analyze/', views.BillAnalysisApi.as_view(), name='bill-analyze'),
    path('query/', views.ConsumerQueryApi.as_view(), name='consumer-query'),

    # Voice
    path('voice/', views.VoiceQueryApi.as_view(), name='voice-query'),

    # Savings
    path('savings/', views.SavingsAnalysisApi.as_view(), name='savings-analysis'),
]
