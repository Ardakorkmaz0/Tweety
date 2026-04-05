"""
Django settings for djangotweet project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-m*u#io8c09*ol#2z3tjy6zjg7(5wwb!xk9ht5y8e*uz^zd3z%q')

# SECURITY WARNING: don't run with debug turned on in production!
# On PythonAnywhere, this should be False

ALLOWED_HOSTS = ['16.171.190.141', 'tweetapptweety.com', 'www.tweetapptweety.com']

DEBUG = False
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



SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = ['https://tweetapptweety.com', 'https://www.tweetapptweety.com']
