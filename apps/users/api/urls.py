"""
User API URLs.
"""
from django.urls import path

from apps.users.api import views

urlpatterns = [
    path('', views.UserListApi.as_view(), name='user-list'),
    path('register/', views.UserCreateApi.as_view(), name='user-register'),
    path('me/', views.UserMeApi.as_view(), name='user-me'),
]
