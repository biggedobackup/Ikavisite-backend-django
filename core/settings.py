import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ─── Security ───────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-ch*z9rc9smlph3$pb47xn0a-g%2rgbph#5(qze-+$fkt8!7h)6')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,10.10.21.197,test.ikavisite.com,*').split(',')

# HTTPS / HSTS (enable in production)
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('DJANGO_HSTS_SUBDOMAINS', 'False') == 'True'
SECURE_HSTS_PRELOAD = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS') else []

# ─── Application definition ──────────────────────────────────────────────────
INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'utilisateurs',
    'entreprise',
    'visites',
    'incidents',
    'alertes_et_notifications',
    'liste_noire',
    'objets_oublies',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'https://c7bc-160-120-114-195.ngrok-free.app',
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://\w+\.ikavisi\.com$',
]
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_ALLOW_HEADERS = [
    'accept', 'authorization', 'content-type', 'user-agent',
    'x-csrftoken', 'x-requested-with',
]

ROOT_URLCONF = 'core.urls'

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
                'alertes_et_notifications.context_processors.alertes_non_lues',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
            'capacity': 1000,
        },
    },
}

# ─── Database ────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'OPTIONS': {
            'pool': os.environ.get('DB_POOL', 'False') == 'True',
        } if os.environ.get('DB_ENGINE') == 'django.db.backends.postgresql' else {},
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '0')),
    }
}

# ─── Redis Cache (fallback to local memory if Redis unavailable) ─────────────
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {'max_connections': 50, 'timeout': 20},
            'MAX_CONNECTIONS': 1000,
            'PICKLE_VERSION': -1,
            'IGNORE_EXCEPTIONS': True,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'ikav',
        'TIMEOUT': 300,
    }
}

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'ikav'

# Session backend (Redis)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ─── Authentication ───────────────────────────────────────────
AUTH_USER_MODEL = 'utilisateurs.Utilisateur'

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/tableau-de-bord/'

AUTHENTICATION_BACKENDS = [
    'core.backends.EmailOrUsernameAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalization ────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Ouagadougou'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ─── Static files ────────────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# ─── Media files ─────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Logging ─────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['mail_admins', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
}

# ─── Security (production overrides) ────────────────────────────────────────
# Uncomment and configure for production:
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
# SECURE_SSL_REDIRECT = True
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# CSRF_TRUSTED_ORIGINS = ['https://api.ikavisi.com']
# DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
# FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880

# ─── Regula (Document scanning) ───────────────────────────────────────────────
REGULA_API_URL = os.environ.get('REGULA_API_URL', 'https://nightly-api.regulaforensics.com')
REGULA_API_KEY = os.environ.get('REGULA_API_KEY', '')

# ─── Django Ninja JWT ─────────────────────────────────────────────────────────
from datetime import timedelta
NINJA_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=36500),  # ~100 ans (n'expire pas tant que l'utilisateur ne se déconnecte pas)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=36500),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'ninja_jwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('ninja_jwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}
