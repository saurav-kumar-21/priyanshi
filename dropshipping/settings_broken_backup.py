"""
Django settings for dropshipping project.
"""

from pathlib import Path
from decouple import config
import os
import sys
from urllib.parse import parse_qs, unquote, urlparse
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from datetime import timedelta
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

def _read_local_env_file():
    """Read local .env file for development"""
    values = {}
    env_path = BASE_DIR / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    values[key.strip()] = value.strip()
    return values

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
_raw_secret_key = _env_or_config('SECRET_KEY', '')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _to_bool(_env_or_config('DEBUG', 'False'), default=False)

def _env_or_config(name, default=''):
    if RUNNING_ON_RENDER:
        return str(os.getenv(name, default)).strip()
    # Prefer repo's .env locally so machine-wide shell vars do not force
    # production behavior during development.
    if name in LOCAL_ENV_VALUES:
        return _read_config(name, default)
    return _env_or_config(name, default)

if _raw_secret_key:
    SECRET_KEY = _raw_secret_key
elif DEBUG:
    # Per-process secret for local development when SECRET_KEY is not set.
    SECRET_KEY = get_random_secret_key()
else:
    raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is False.')

ALLOWED_HOSTS = _csv_to_list(_env_or_config('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver'))
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

IS_PRODUCTION = _to_bool(_env_or_config('DJANGO_PRODUCTION', 'False'), default=False)
if not IS_PRODUCTION and not DEBUG:
    IS_PRODUCTION = any(not _is_local_host(host) for host in ALLOWED_HOSTS)
if RUNNING_ON_RENDER:
    IS_PRODUCTION = True

if IS_PRODUCTION and (SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured('Use a strong, non-default SECRET_KEY when running in production.')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django.contrib.sites',
    # 'allauth',
    # 'allauth.account',
    # 'allauth.socialaccount',
    # 'crispy_forms',
    # 'crispy_bootstrap5',
    # 'phonenumber_field',
    # 'django_extensions',
    # 'django_filters',
    
    # Local apps
    'core',
    'accounts',
    'products',
    'orders',
    'sellers',
    'cart',
    'reviews',
    'payments',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'core.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.DynamicCSRFMiddleware',
]

ROOT_URLCONF = 'dropshipping.urls'

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
                'django.template.context_processors.static',
                'core.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'dropshipping.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# Priority:
# 1) DATABASE_URL (common on Render/Railway/Heroku)
# 2) DB_ENGINE + DB_NAME + DB_USER + DB_PASSWORD + DB_HOST + DB_PORT
# 3) Local SQLite fallback for development

DATABASE_URL = _db_value('DATABASE_URL', '')
if not DATABASE_URL:
    DATABASE_URL = _db_value('POSTGRES_URL', '')
if not DATABASE_URL:
    DATABASE_URL = _db_value('POSTGRESQL_URL', '')

RAW_DB_ENGINE = _db_value('DB_ENGINE', '')
DB_ENGINE_ALIASES = {
    'sqlite3': 'django.db.backends.sqlite3',
    'postgres': 'django.db.backends.postgresql',
    'postgresql': 'django.db.backends.postgresql',
    'mysql': 'django.db.backends.mysql',
}
DB_ENGINE = DB_ENGINE_ALIASES.get(RAW_DB_ENGINE, RAW_DB_ENGINE)

if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    scheme = (parsed.scheme or '').lower()

    if scheme in {'postgres', 'postgresql'}:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': unquote((parsed.path or '').lstrip('/')),
                'USER': unquote(parsed.username or ''),
                'PASSWORD': unquote(parsed.password or ''),
                'HOST': parsed.hostname or '',
                'PORT': str(parsed.port or ''),
            }
        }
        
    elif scheme in {'sqlite', 'sqlite3'}:
        sqlite_path = unquote((parsed.path or '').lstrip('/'))
        sqlite_name = sqlite_path if os.path.isabs(sqlite_path) else str(BASE_DIR / sqlite_path)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': sqlite_name,
            }
        }
    else:
        raise ImproperlyConfigured(f"Unsupported DATABASE_URL scheme: '{scheme}'")
elif DB_ENGINE:
    default_db_name = str(BASE_DIR / 'db.sqlite3') if DB_ENGINE == 'django.db.backends.sqlite3' else ''
    db_name = _db_value('DB_NAME', '') or _db_value('PGDATABASE', default_db_name)
    db_user = _db_value('DB_USER', '') or _db_value('PGUSER', '')
    db_password = _db_value('DB_PASSWORD', '') or _db_value('PGPASSWORD', '')
    db_host = _db_value('DB_HOST', '') or _db_value('PGHOST', '')
    db_port = _db_value('DB_PORT', '') or _db_value('PGPORT', '5432')

    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': db_name,
        }
    }
    if DB_ENGINE != 'django.db.backends.sqlite3':
        DATABASES['default'].update({
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
        })

if IS_PRODUCTION and DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    raise ImproperlyConfigured(
        'SQLite is not supported in production. Configure PostgreSQL with DATABASE_URL or DB_* variables.'
    )

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        'OPTIONS': {
            'common_passwords': ['password', '123456', 'qwerty'],
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_METADATA_CLASS': 'core.drf_metadata.EmptyMetadata',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('DRF_THROTTLE_ANON', default='120/min'),
        'user': config('DRF_THROTTLE_USER', default='240/min'),
    },
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}

# Session Security Settings
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000'] if DEBUG else []

# Password Security Settings
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        'OPTIONS': {
            'common_passwords': ['password', '123456', 'qwerty'],
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
]

# Django Allauth
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

CURRENT_COMMAND = sys.argv[1] if len(sys.argv) > 1 else ''
SKIP_DB_GUARD_COMMANDS = {'collectstatic'}

if (
    RUNNING_ON_RENDER
    and DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
    and CURRENT_COMMAND not in SKIP_DB_GUARD_COMMANDS
):
    db_host = (DATABASES['default'].get('HOST') or '').strip()
    if _is_local_host(db_host):
        raise ImproperlyConfigured(
            'Render runtime is trying to use localhost PostgreSQL. Set DATABASE_URL from your Render PostgreSQL service.'
        )

def _read_config(name, default=''):
    return str(config(name, default=default)).strip()

def _env_or_config(name, default=''):
    if RUNNING_ON_RENDER:
        return str(os.getenv(name, default)).strip()
    # Prefer repo's .env locally so machine-wide shell vars do not force
    # production behavior during development.
    if name in LOCAL_ENV_VALUES:
        return _read_config(name, default)
    return _env_or_config(name, default)

def _to_bool(value, default=False):
    """Parse environment booleans safely without raising."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on', 'y', 't', 'debug', 'development'}:
        return True
    if normalized in {'0', 'false', 'no', 'off', 'n', 'f', 'prod', 'production', 'release'}:
        return False
    return default

def _csv_to_list(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(',') if item.strip()]

LOCAL_ENV_VALUES = _read_local_env_file()

def _is_local_host(host):
    normalized = (host or '').strip().lower()
    if not normalized:
        return True
    if ':' in normalized:
        normalized = normalized.split(':', 1)[0]
    return normalized in {'localhost', '127.0.0.1', 'testserver'}

def _read_config(name, default=''):
    return str(config(name, default=default)).strip()

def _env_or_config(name, default=''):
    return str(config(name, default=default)).strip()

def _env_or_config(name, default=''):
    if RUNNING_ON_RENDER:
        return str(os.getenv(name, default)).strip()
    # Prefer repo's .env locally so machine-wide shell vars do not force
    # production behavior during development.
    if name in LOCAL_ENV_VALUES:
        return _read_config(name, default)
    return _env_or_config(name, default)
