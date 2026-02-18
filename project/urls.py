"""
URL configuration for blog project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from apps.users import views as user_views
from apps.core import views as core_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Hello World
    path('hello/', core_views.hello_world, name='hello-world'),
    path('server-ip/', core_views.server_ip, name='server-ip'),
    path('proxy-test/', core_views.proxy_test, name='proxy-test'),
    path('tts-test/', core_views.tts_test, name='tts-test'),

    # Authentication
    path('', user_views.home_view, name='home'),
    path('login/', user_views.login_view, name='login'),
    path('register/', user_views.register_view, name='register'),
    path('logout/', user_views.logout_view, name='logout'),
    path('dashboard/', user_views.dashboard_view, name='dashboard'),
    path('users/', user_views.user_list_view, name='user-list'),

    # API
    path('api/users/', include('apps.users.api.urls')),
    path('api/consumer/', include('apps.consumer.api.urls')),
    path('api/operations/', include('apps.operations.api.urls')),
    path('api/ai/', include('apps.ai_engine.api.urls')),

    # WhatsApp Webhook
    path('webhook/whatsapp/', include('apps.whatsapp.api.urls')),

    # Nawwar Dashboard
    path('nawwar/', include('apps.dashboard.urls')),
]

# Debug toolbar URLs (only in development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Only include debug_toolbar if it's installed in INSTALLED_APPS
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        try:
            import debug_toolbar
            urlpatterns = [
                path('__debug__/', include(debug_toolbar.urls)),
            ] + urlpatterns
        except ImportError:
            pass
