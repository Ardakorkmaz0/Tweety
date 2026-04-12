"""
Django settings for djangotweet project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
# Set ENVIRONMENT=production on your server; defaults to development for local use
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

DEBUG = ENVIRONMENT == 'development'

# SECURITY WARNING: keep the secret key used in production secret!
# In dev we fall back to a placeholder so local setup is frictionless,
# but production MUST provide its own SECRET_KEY via the environment.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-me')
if ENVIRONMENT == 'production' and (
    not SECRET_KEY or SECRET_KEY.startswith('django-insecure-')
):
    raise RuntimeError(
        'SECRET_KEY environment variable must be set in production.'
    )

if ENVIRONMENT == 'production':
    ALLOWED_HOSTS = ['16.171.190.141', 'tweetapptweety.com', 'www.tweetapptweety.com']
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
# Application definition
INSTALLED_APPS = [
    'tweetapp.apps.TweetappConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise must be right below SecurityMiddleware to serve CSS/JS in production
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tweetapp.middleware.UpdateLastActiveMiddleware',
]

ROOT_URLCONF = 'djangotweet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tweetapp.context_processors.unread_notifications',
                'tweetapp.context_processors.global_sidebar_data',
            ],
        },
    },
]

WSGI_APPLICATION = 'djangotweet.wsgi.application'

# Database
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise optimization for production
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'tweetapp:listtweet'

# Web Push Notifications (VAPID)
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BIjSVQULymkJphvbspxGsFSbntX9wcRQINXk9mTTx06Map9HEHbNml059r5-ce_-KzYb4JRd2iGEv0vbxHd1vSk')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', 'h6J_7e9pS41hivTaGoAetv6Hox-maTPmh2Jyn1GTMGU')

VAPID_ADMIN_EMAIL = os.environ.get('VAPID_ADMIN_EMAIL', 'mailto:admin@tweety.com')

# Email Configuration
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@tweety.com')

if EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Production-only security settings
if ENVIRONMENT == 'production':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = ['https://tweetapptweety.com', 'https://www.tweetapptweety.com']

    # HSTS — start at 1 day so a misconfig is recoverable; bump to 31536000
    # (1 year) once you're confident HTTPS is stable.
    SECURE_HSTS_SECONDS = 86400
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False

    # Misc hardening headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

    # Cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
