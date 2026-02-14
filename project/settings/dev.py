"""
Django Development Settings.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Development-only apps
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Debug Toolbar
INTERNAL_IPS = ['127.0.0.1']

# Database - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email - Console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cache - Local memory for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Logging - More verbose in development
LOGGING['root']['level'] = 'DEBUG'
