"""
Django Local Development Settings.
Uses PostgreSQL database with DEBUG mode for local testing.
"""
from .base import *
from decouple import config, Csv

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']

# Remove debug_toolbar if it's in MIDDLEWARE
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]

# Database - PostgreSQL (same as production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='django_blog_db'),
        'USER': config('DB_USER', default='django_blog_db'),
        'PASSWORD': config('DB_PASSWORD', default='admin123'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432', cast=int),
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

# Static files - Simple serving for development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Logging - More verbose in development
LOGGING['root']['level'] = 'INFO'
