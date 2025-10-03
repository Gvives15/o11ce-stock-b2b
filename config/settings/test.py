"""
Settings específicos para tests
"""

from .base import *
import os

# TESTING CONFIGURATION
# ------------------------------------------------------------------------------

# Usar base de datos en memoria para tests rápidos o PostgreSQL de test según configuración
if os.environ.get('USE_TEST_DB') == 'postgres':
    # Configuración para usar PostgreSQL de test (Docker)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('TEST_DB_NAME', 'test_bff'),
            'USER': os.environ.get('TEST_DB_USER', 'test_user'),
            'PASSWORD': os.environ.get('TEST_DB_PASSWORD', 'test_password'),
            'HOST': os.environ.get('TEST_DB_HOST', 'localhost'),
            'PORT': os.environ.get('TEST_DB_PORT', '5433'),
            'TEST': {
                'NAME': 'test_bff_test',  # Base de datos específica para tests
            },
        }
    }
else:
    # Usar SQLite en memoria para tests rápidos (por defecto)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# CACHE CONFIGURATION FOR TESTS
# ------------------------------------------------------------------------------
if os.environ.get('USE_TEST_REDIS') == 'true':
    # Usar Redis de test (Docker)
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('TEST_REDIS_URL', 'redis://localhost:6380/0'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    # Usar cache local para tests
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# CELERY CONFIGURATION FOR TESTS
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = os.environ.get('TEST_CELERY_BROKER_URL', 'memory://')
CELERY_RESULT_BACKEND = 'cache+memory://'

# EMAIL CONFIGURATION FOR TESTS
# ------------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# LOGGING CONFIGURATION FOR TESTS
# ------------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
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
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# SECURITY SETTINGS FOR TESTS
# ------------------------------------------------------------------------------
SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

# STATIC FILES FOR TESTS
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# PASSWORD VALIDATION - Simplified for tests
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = []

# TESTING FLAGS
# ------------------------------------------------------------------------------
TESTING = True

# DISABLE MIGRATIONS FOR FASTER TESTS
# ------------------------------------------------------------------------------
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

# Uncomment to disable migrations in tests (faster but may miss migration issues)
# MIGRATION_MODULES = DisableMigrations()

# EVENT BUS CONFIGURATION FOR TESTS
# ------------------------------------------------------------------------------
# Configuración específica para tests del Event Bus
EVENT_BUS_CONFIG = {
    'redis_url': os.environ.get('TEST_REDIS_URL', 'redis://localhost:6380/0'),
    'max_retries': 1,  # Menos reintentos en tests
    'retry_delay': 0.1,  # Delay más corto en tests
}