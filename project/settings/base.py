"""
Django Base Settings - Shared across all environments.
"""
from decouple import config, Csv
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# python-decouple automatically reads .env file from project root
# No need to manually load it - it just works!

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.blog',
    'apps.consumer',
    'apps.operations',
    'apps.ai_engine',
    'apps.whatsapp',
    'apps.dashboard',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'
ASGI_APPLICATION = 'project.asgi.application'

# Database - Override in dev.py and prod.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '120/minute',
        'ai_endpoint': '10/minute',
        'whatsapp_webhook': '60/minute',
    },
}

# =============================================================================
# Nawwar AI Platform Configuration
# =============================================================================

# AI Provider Keys
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')

# AI Model Configuration
AI_CONFIG = {
    'VISION_MODEL': 'gpt-4o',
    'WHISPER_MODEL': 'whisper-1',
    'CLAUDE_MODEL': 'claude-sonnet-4-20250514',
    'EMBEDDING_MODEL': 'text-embedding-3-small',
    'MAX_TOKENS': 4096,
    'TEMPERATURE': 0.3,
}

# JEPCO Configuration (real API — JWT cookie auth)
JEPCO_CONFIG = {
    'USER_TOKEN': config('JEPCO_USER_TOKEN', default=''),
    'ESERVICES_TOKEN': config('JEPCO_ESERVICES_TOKEN', default=''),
    'AUTH_TOKEN': config('JEPCO_AUTH_TOKEN', default=''),  # legacy fallback
    'MOBILE_NUMBER': config('JEPCO_MOBILE_NUMBER', default=''),
    'DEFAULT_FILE_NUMBER': config('JEPCO_DEFAULT_FILE_NUMBER', default=''),
    'LANGUAGE': config('JEPCO_LANGUAGE', default='AR'),
    'TIMEOUT': 30,
}

# WhatsApp Configuration (4whats.net API)
WHATSAPP_CONFIG = {
    'INSTANCE_ID': config('WHATSAPP_INSTANCE_ID', default='140789'),
    'TOKEN': config('WHATSAPP_TOKEN', default='2b1272f8-bc6d-49d0-8041-3be09c097287'),
    'API_URL': 'https://api.4whats.net',
}

# Site URL for generating external links (e.g. WhatsApp welcome messages)
SITE_URL = config('SITE_URL', default='')

# WhatsApp webhook HMAC secret for signature verification
WHATSAPP_WEBHOOK_SECRET = config('WHATSAPP_WEBHOOK_SECRET', default='')

# AI cost budget limits
AI_DAILY_BUDGET_USD = config('AI_DAILY_BUDGET_USD', default=5.0, cast=float)
AI_MONTHLY_BUDGET_USD = config('AI_MONTHLY_BUDGET_USD', default=100.0, cast=float)

# Data retention (days)
SESSION_EXPIRY_DAYS = config('SESSION_EXPIRY_DAYS', default=90, cast=int)
MESSAGE_RETENTION_DAYS = config('MESSAGE_RETENTION_DAYS', default=180, cast=int)

# Max message length stored in DB
MAX_MESSAGE_LENGTH = 4096

# ChromaDB Configuration
CHROMADB_PATH = BASE_DIR / 'chromadb_data'

# Edge-TTS Configuration
TTS_CONFIG = {
    'MALE_VOICE': 'ar-JO-TaimurNeural',
    'FEMALE_VOICE': 'ar-JO-SanaNeural',
    'DEFAULT_VOICE': 'ar-JO-TaimurNeural',
}

# CEGCO Plant Configuration
CEGCO_PLANTS = {
    'AQABA': {
        'name': 'Aqaba Thermal Power Station',
        'name_ar': 'محطة العقبة الحرارية',
        'capacity_mw': 390,
        'type': 'steam',
        'fuel': 'multi-fuel (HFO/natural gas)',
        'year': 1985,
        'turbines': 5,
        'location': {'lat': 29.5167, 'lon': 35.0000},
    },
    'RISHA': {
        'name': 'Risha Gas Power Station',
        'name_ar': 'محطة الريشة الغازية',
        'capacity_mw': 150,
        'type': 'gas',
        'fuel': 'natural gas',
        'year': 1989,
        'turbines': 4,
        'location': {'lat': 32.2500, 'lon': 38.2500},
    },
    'REHAB': {
        'name': 'Rehab Combined Cycle Power Station',
        'name_ar': 'محطة رحاب',
        'capacity_mw': 297,
        'type': 'ccgt',
        'fuel': 'natural gas',
        'year': 1990,
        'turbines': 6,
        'location': {'lat': 32.3000, 'lon': 36.1000},
    },
}

# EMRC Tariff Configuration (Jordanian fils per kWh)
EMRC_TARIFFS = {
    'RESIDENTIAL': [
        {'tier': 1, 'range': '1-160', 'min_kwh': 0, 'max_kwh': 160, 'rate_fils': 33},
        {'tier': 2, 'range': '161-300', 'min_kwh': 161, 'max_kwh': 300, 'rate_fils': 72},
        {'tier': 3, 'range': '301-500', 'min_kwh': 301, 'max_kwh': 500, 'rate_fils': 86},
        {'tier': 4, 'range': '501-600', 'min_kwh': 501, 'max_kwh': 600, 'rate_fils': 114},
        {'tier': 5, 'range': '601-750', 'min_kwh': 601, 'max_kwh': 750, 'rate_fils': 158},
        {'tier': 6, 'range': '751-1000', 'min_kwh': 751, 'max_kwh': 1000, 'rate_fils': 188},
        {'tier': 7, 'range': '1000+', 'min_kwh': 1001, 'max_kwh': 99999, 'rate_fils': 265},
    ],
    'COMMERCIAL': [
        {'tier': 1, 'range': 'all', 'min_kwh': 0, 'max_kwh': 99999, 'rate_fils': 115},
    ],
    'INDUSTRIAL': [
        {'tier': 1, 'range': 'all', 'min_kwh': 0, 'max_kwh': 99999, 'rate_fils': 76},
    ],
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
