"""
WhatsApp API URLs.
"""
from django.urls import path

from apps.whatsapp.api import views

urlpatterns = [
    path('', views.WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
]
