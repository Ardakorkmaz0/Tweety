"""
Django settings for djangotweet project.
Combined with automated .env generation.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Define the path to the .env file
ENV_PATH = BASE_DIR / '.env'

# Create .env file if it doesn't exist
if not ENV_PATH.exists():
    # Generate a unique secret key for local development
    new_secret_key = get_random_secret_key()
    
    with open(ENV_PATH, 'w') as f:
        f.write(f"DEBUG=True\n")
        f.write(f"SECRET_KEY={new_secret_key}\n")
        f.write(f"ALLOWED_HOSTS=localhost,127.0.0.1\n")
    print(f"--- INFO: New .env file has been generated at {ENV_PATH} ---")

# Load environment variables from the .env file
load_dotenv(ENV_PATH)

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY')
# Convert the string 'True'/'False' from .env to a Python Boolean
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
# Split comma-separated string into a list
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

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
        'DIRS': [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = 'djangotweet.wsgi.application'

# Database
# Using SQLite for development as it's portable
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
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/tweetapp/'