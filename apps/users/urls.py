"""
User URLs - includes both API and template-based views.
"""
from django.urls import path, include

from apps.users import views

app_name = 'users'

urlpatterns = [
    path('api/', include('apps.users.api.urls')),
    path('list/', views.user_list_view, name='list'),
]
