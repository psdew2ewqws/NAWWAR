"""
Dashboard URLs — served under /nawwar/.
"""
from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    # Operations
    path('operations/', views.operations_index, name='operations-index'),
    path('operations/<str:plant_key>/', views.operations_plant_detail, name='operations-plant-detail'),

    # Consumer
    path('consumer/', views.consumer_index, name='consumer-index'),
    path('consumer/chat/<str:session_key>/', views.consumer_chat, name='consumer-chat'),

    # API (for AJAX updates)
    path('api/plant/<str:plant_key>/', views.api_plant_data, name='api-plant-data'),

    # Consumer Chat API
    path('api/chat/', views.api_chat, name='api-chat'),
    path('api/chat/scan/', views.api_chat_scan, name='api-chat-scan'),
    path('api/chat/voice/', views.api_chat_voice, name='api-chat-voice'),

    # JEPCO API (real API with demo fallback)
    path('api/jepco/customer/', views.api_jepco_customer, name='api-jepco-customer'),
    path('api/jepco/bills/<str:file_number>/', views.api_jepco_bills, name='api-jepco-bills'),
    path('api/jepco/complaints/', views.api_jepco_complaints, name='api-jepco-complaints'),
    path('api/jepco/provinces/', views.api_jepco_provinces, name='api-jepco-provinces'),
    path('api/jepco/meter/<str:meter_number>/', views.api_jepco_verify_meter, name='api-jepco-meter'),
    path('api/jepco/smart-meter/<str:file_number>/', views.api_jepco_smart_meter, name='api-jepco-smart-meter'),
    path('api/jepco/analyze/<str:file_number>/', views.api_jepco_analyze, name='api-jepco-analyze'),
    path('api/jepco/account-summary/', views.api_jepco_account_summary, name='api-jepco-account-summary'),
]
