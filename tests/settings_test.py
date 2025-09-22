"""
Test-specific Django settings.
Optimized for fast, reliable testing with proper service mocking.
"""
import os
from config.settings import *

# Test database - use in-memory SQLite for speed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Use test database URL if provided (for CI)
if 'DATABASE_URL' in os.environ:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(os.environ['DATABASE_URL'])

# Cache configuration for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Use Redis if available (for CI), otherwise use dummy backend
if 'REDIS_URL' in os.environ:
    try:
        import django_redis
        CACHES['default'] = {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ['REDIS_URL'],
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 2,  # Reduced for tests
                    'retry_on_timeout': True,
                }
            }
        }
    except ImportError:
        # Keep default locmem cache if django_redis is not available
        pass

# Celery configuration for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Override with Redis if available (for integration tests)
if 'REDIS_URL' in os.environ:
    CELERY_BROKER_URL = os.environ['REDIS_URL']
    CELERY_RESULT_BACKEND = os.environ['REDIS_URL']

# Email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

# Use real migrations in CI, disable locally for speed
if not os.environ.get('CI'):
    MIGRATION_MODULES = DisableMigrations()

# Logging configuration for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'WARNING',  # Reduce noise in tests
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',  # Keep app logs visible
            'propagate': False,
        },
    },
}

# Security settings for tests
SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Disable CSRF for API tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Password validation (simplified for tests)
AUTH_PASSWORD_VALIDATORS = []

# Static files (not needed for tests)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files (use temp directory)
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

# Disable rate limiting in tests
RATELIMIT_ENABLE = False

# Test-specific apps (django_extensions already included in main settings)
# INSTALLED_APPS += [
#     'django_extensions',  # Already included in main settings
# ]

# Metrics collection (disabled in tests unless explicitly enabled)
METRICS_ENABLED = os.environ.get('TEST_METRICS', 'false').lower() == 'true'

# Sentry (disabled in tests)
SENTRY_DSN = None

# Performance settings for tests
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Test runner configuration
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Pytest configuration
PYTEST_TIMEOUT = 300  # 5 minutes max per test

# Factory Boy settings
FACTORY_FOR_DJANGO_MODELS = True

# Test data settings
TEST_DATA_DIR = os.path.join(BASE_DIR, 'tests', 'data')
TEST_FIXTURES_DIR = os.path.join(BASE_DIR, 'tests', 'fixtures')

# Health check settings for tests
HEALTH_CHECK_TIMEOUT = 1  # Faster timeouts in tests
HEALTH_CHECK_CACHE_TIMEOUT = 5

# Stock settings for tests
FEFO_BATCH_SIZE = 10  # Smaller batches for faster tests
STOCK_ALERT_BATCH_SIZE = 5

# Cache settings for tests
CACHE_TIMEOUT_SHORT = 10  # Shorter timeouts for tests
CACHE_TIMEOUT_MEDIUM = 30
CACHE_TIMEOUT_LONG = 60

# Notification settings for tests
EMAIL_TIMEOUT = 2  # Faster email timeouts
SMTP_TIMEOUT = 2

# Concurrency settings for tests
MAX_CONCURRENT_ORDERS = 2  # Reduced for tests
FEFO_LOCK_TIMEOUT = 5

# Test database optimization
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default']['OPTIONS'] = {
        'timeout': 20,
        'init_command': 'PRAGMA journal_mode=WAL;',
    }

# Test-specific middleware (remove some for speed)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Skip some middleware in tests for speed
]

# API settings for tests
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,  # Smaller pages for tests
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

# Internationalization for tests
USE_I18N = False  # Disable for speed
USE_L10N = False
USE_TZ = True

# Time zone for tests
TIME_ZONE = 'UTC'

print(f"✓ Test settings loaded - Database: {DATABASES['default']['ENGINE']}")
print(f"✓ Cache backend: {CACHES['default']['BACKEND']}")
print(f"✓ Celery eager mode: {CELERY_TASK_ALWAYS_EAGER}")
print(f"✓ Redis URL: {os.environ.get('REDIS_URL', 'Not configured')}")