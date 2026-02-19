"""
SoulSeer Django settings. Uses django-environ for .env loading.
"""
import os
from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-CHANGE-ME-IN-PRODUCTION')
DEBUG = env('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Database
import dj_database_url
DATABASE_URL = env('DATABASE_URL', default=env('NEON_DB_CONNECTION_STRING', default=''))
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('PGDATABASE', default='neondb'),
            'USER': env('PGUSER', default='neondb_owner'),
            'PASSWORD': env('PGPASSWORD', default=''),
            'HOST': env('PGHOST', default='localhost'),
            'PORT': env('PGPORT', default='5432'),
            'OPTIONS': {'sslmode': env('PGSSLMODE', default='require')},
        }
    }

# Redis / Celery
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_BEAT_SCHEDULE = {
    'billing-tick': {
        'task': 'readings.tasks.billing_tick',
        'schedule': 60.0,
    },
    'expire-grace-periods': {
        'task': 'readings.tasks.expire_grace_periods',
        'schedule': 30.0,
    },
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Auth0
AUTH0_DOMAIN = env('AUTH0_DOMAIN', default='').rstrip('/')
if not AUTH0_DOMAIN:
    _ident = env('AUTH0_IDENTIFIER', default='')
    if _ident:
        AUTH0_DOMAIN = _ident.replace('https://', '').split('/')[0]
AUTH0_AUDIENCE = env('AUTH0_AUDIENCE', default=env('AUTH0_IDENTIFIER', default=''))
AUTH0_APP_ID = env('AUTH0_APP_ID', default='')
AUTH0_CLIENT_SECRET = env('AUTH0_CLIENT_SECRET', default='')

# Agora
AGORA_APP_ID = env('AGORA_APP_ID', default='')
AGORA_CERTIFICATE = env('AGORA_SECURITY_CERTIFICATE', default='')
AGORA_CHAT_APP_ID = env('AGORA_CHAT_APP_ID', default='')
AGORA_CHAT_WEBSOCKET_ADDRESS = env('AGORA_CHAT_WEBSOCKET_ADDRESS', default='')
AGORA_CHAT_REST_API = env('AGORA_CHAT_REST_API', default='')

# Stripe
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='').strip()
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='').strip()
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SIGNING_SECRET', default='').strip()

# R2 / S3
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
R2_BUCKET = env('R2_BUCKET', default='')
R2_ENDPOINT = env('R2_ENDPOINT', default='')
R2_CUSTOM_DOMAIN = env('R2_CUSTOM_DOMAIN', default='')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_htmx',
    'rest_framework',
    'core',
    'accounts',
    'wallets',
    'readers',
    'readings',
    'messaging',
    'scheduling',
    'live',
    'shop',
    'community',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'soulseer.urls'
WSGI_APPLICATION = 'soulseer.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.settings_ctx',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'

# Custom user model placeholder - we'll use extended profile
# AUTH_USER_MODEL = 'accounts.User'  # Optional if using profile extension

# Sentry
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()], traces_sample_rate=0.1)
# Security settings (production-ready)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
        "script-src": ("'self'", "cdn.jsdelivr.net", "*.agora.io", "https://js.stripe.com"),
        "connect-src": ("'self'", "*.agora.io", "https://api.stripe.com"),
        "style-src": ("'self'", "cdn.jsdelivr.net", "'unsafe-inline'"),
        "img-src": ("'self'", "data:", "https:"),
        "font-src": ("'self'", "cdn.jsdelivr.net"),
    }

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'readings': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'wallets': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}