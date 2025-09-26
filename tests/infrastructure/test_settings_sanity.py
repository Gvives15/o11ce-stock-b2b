"""
Tests de sanidad para configuración del sistema.
Bloque 0 - Pre-flight: Verificación de variables críticas presentes.

Objetivo: Verificar que las variables críticas estén presentes y configuradas correctamente:
- DATABASE_URL
- REDIS_URL  
- JWT_SECRET
- Otras variables críticas del sistema
"""
import os
import pytest
from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import dj_database_url


class TestCriticalSettingsSanity(TestCase):
    """Tests de sanidad para configuraciones críticas del sistema."""
    
    def test_database_url_is_configured(self):
        """Test que DATABASE_URL esté configurada y sea válida."""
        # Verificar que DATABASE_URL existe en el entorno
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            # Si no está en el entorno, verificar que tengamos configuración de DB válida
            self.assertIn('default', settings.DATABASES)
            db_config = settings.DATABASES['default']
            self.assertIn('ENGINE', db_config)
            self.assertIn('NAME', db_config)
        else:
            # Si está en el entorno, verificar que sea una URL válida
            try:
                parsed_db = dj_database_url.parse(database_url)
                self.assertIn('ENGINE', parsed_db)
                self.assertIn('NAME', parsed_db)
            except Exception as e:
                self.fail(f"DATABASE_URL is invalid: {e}")
    
    def test_redis_url_is_configured(self):
        """Test que REDIS_URL esté configurada para cache y Celery."""
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            # Si REDIS_URL está configurada, verificar formato
            self.assertTrue(
                redis_url.startswith('redis://') or redis_url.startswith('rediss://'),
                f"REDIS_URL debe comenzar con redis:// o rediss://, got: {redis_url}"
            )
            
            # Verificar que contenga host y puerto
            self.assertIn(':', redis_url.split('//')[1])
        
        # Verificar configuración de cache
        self.assertIn('default', settings.CACHES)
        cache_config = settings.CACHES['default']
        self.assertIn('BACKEND', cache_config)
        
        # Si usamos Redis, verificar configuración
        if 'redis' in cache_config['BACKEND'].lower():
            self.assertIn('LOCATION', cache_config)
    
    def test_jwt_secret_is_configured_and_secure(self):
        """Test que JWT_SECRET esté configurada y sea segura."""
        jwt_secret = os.environ.get('JWT_SECRET')
        
        # Verificar que existe
        self.assertIsNotNone(jwt_secret, "JWT_SECRET debe estar configurada")
        
        # Verificar que no sea el valor por defecto inseguro
        insecure_defaults = ['devjwt', 'your-super-secret-jwt-key-change-in-production', '']
        self.assertNotIn(jwt_secret, insecure_defaults, 
                        "JWT_SECRET no debe usar valores por defecto inseguros")
        
        # Verificar longitud mínima
        self.assertGreaterEqual(len(jwt_secret), 32, 
                               "JWT_SECRET debe tener al menos 32 caracteres")
        
        # Verificar que esté configurada en Django settings
        self.assertTrue(hasattr(settings, 'SIMPLE_JWT'))
        self.assertEqual(settings.SIMPLE_JWT['SIGNING_KEY'], jwt_secret)
    
    def test_secret_key_is_configured_and_secure(self):
        """Test que SECRET_KEY de Django esté configurada y sea segura."""
        secret_key = settings.SECRET_KEY
        
        # Verificar que existe
        self.assertIsNotNone(secret_key, "SECRET_KEY debe estar configurada")
        
        # Verificar que no sea el valor por defecto inseguro
        self.assertNotIn('django-insecure', secret_key, 
                        "SECRET_KEY no debe usar el valor por defecto inseguro")
        
        # Verificar longitud mínima
        self.assertGreaterEqual(len(secret_key), 50, 
                               "SECRET_KEY debe tener al menos 50 caracteres")
    
    def test_debug_is_properly_configured(self):
        """Test que DEBUG esté configurado apropiadamente según el entorno."""
        debug_env = os.environ.get('DEBUG', '0')
        
        # Verificar que DEBUG en settings coincida con la variable de entorno
        expected_debug = debug_env == '1'
        self.assertEqual(settings.DEBUG, expected_debug)
        
        # En producción (DEBUG=False), verificar configuraciones de seguridad
        if not settings.DEBUG:
            self.assertTrue(len(settings.ALLOWED_HOSTS) > 0, 
                           "ALLOWED_HOSTS debe estar configurado cuando DEBUG=False")
    
    def test_celery_broker_url_is_configured(self):
        """Test que CELERY_BROKER_URL esté configurada."""
        celery_broker = os.environ.get('CELERY_BROKER_URL')
        
        if celery_broker:
            # Verificar formato de URL
            valid_prefixes = ['redis://', 'rediss://', 'amqp://', 'memory://']
            self.assertTrue(
                any(celery_broker.startswith(prefix) for prefix in valid_prefixes),
                f"CELERY_BROKER_URL debe usar un protocolo válido: {valid_prefixes}"
            )
        
        # Verificar configuración en settings si existe
        if hasattr(settings, 'CELERY_BROKER_URL'):
            self.assertIsNotNone(settings.CELERY_BROKER_URL)
    
    def test_email_configuration_is_present(self):
        """Test que la configuración de email esté presente."""
        # Verificar backend de email
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
        self.assertIsNotNone(settings.EMAIL_BACKEND)
        
        # Si usamos SMTP, verificar configuración básica
        if 'smtp' in settings.EMAIL_BACKEND.lower():
            email_host = getattr(settings, 'EMAIL_HOST', None)
            email_port = getattr(settings, 'EMAIL_PORT', None)
            
            # En entornos de desarrollo, permitir configuraciones locales
            if not settings.DEBUG:
                self.assertIsNotNone(email_host, "EMAIL_HOST debe estar configurado")
                self.assertIsNotNone(email_port, "EMAIL_PORT debe estar configurado")
    
    def test_cors_configuration_is_secure(self):
        """Test que la configuración de CORS sea segura."""
        # Verificar que CORS_ALLOW_ALL_ORIGINS no esté habilitado en producción
        if not settings.DEBUG:
            cors_allow_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)
            self.assertFalse(cors_allow_all, 
                           "CORS_ALLOW_ALL_ORIGINS no debe estar habilitado en producción")
            
            # Verificar que tengamos orígenes específicos configurados
            cors_allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            self.assertTrue(len(cors_allowed_origins) > 0, 
                          "CORS_ALLOWED_ORIGINS debe tener orígenes específicos en producción")
    
    def test_time_zone_is_configured(self):
        """Test que TIME_ZONE esté configurada correctamente."""
        self.assertTrue(hasattr(settings, 'TIME_ZONE'))
        self.assertIsNotNone(settings.TIME_ZONE)
        
        # Verificar que USE_TZ esté habilitado
        self.assertTrue(settings.USE_TZ, "USE_TZ debe estar habilitado")
    
    def test_static_and_media_configuration(self):
        """Test que la configuración de archivos estáticos y media esté presente."""
        # Verificar configuración de archivos estáticos
        self.assertTrue(hasattr(settings, 'STATIC_URL'))
        self.assertIsNotNone(settings.STATIC_URL)
        
        # En producción, verificar STATIC_ROOT
        if not settings.DEBUG:
            self.assertTrue(hasattr(settings, 'STATIC_ROOT'))
            self.assertIsNotNone(settings.STATIC_ROOT)
        
        # Verificar configuración de media
        self.assertTrue(hasattr(settings, 'MEDIA_URL'))
        self.assertTrue(hasattr(settings, 'MEDIA_ROOT'))


@pytest.mark.infrastructure
class TestEnvironmentVariablesSanity:
    """Tests de sanidad usando pytest para variables de entorno."""
    
    def test_critical_environment_variables_present(self):
        """Test que las variables de entorno críticas estén presentes."""
        critical_vars = [
            'SECRET_KEY',
            'JWT_SECRET',
        ]
        
        missing_vars = []
        for var in critical_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        assert len(missing_vars) == 0, f"Variables críticas faltantes: {missing_vars}"
    
    def test_database_configuration_variables(self):
        """Test que las variables de configuración de base de datos estén presentes."""
        # Al menos una de estas debe estar presente
        db_vars = ['DATABASE_URL', 'POSTGRES_DB']
        
        has_db_config = any(os.environ.get(var) for var in db_vars)
        assert has_db_config, f"Al menos una variable de DB debe estar presente: {db_vars}"
    
    def test_redis_configuration_variables(self):
        """Test que las variables de Redis estén configuradas si se usan."""
        redis_url = os.environ.get('REDIS_URL')
        celery_broker = os.environ.get('CELERY_BROKER_URL')
        
        # Si usamos Redis para cache o Celery, verificar configuración
        if redis_url or celery_broker:
            if redis_url:
                assert redis_url.startswith(('redis://', 'rediss://')), \
                    f"REDIS_URL debe ser una URL válida: {redis_url}"
            
            if celery_broker and 'redis' in celery_broker:
                assert celery_broker.startswith(('redis://', 'rediss://')), \
                    f"CELERY_BROKER_URL debe ser una URL Redis válida: {celery_broker}"
    
    def test_security_variables_in_production(self):
        """Test que las variables de seguridad estén configuradas en producción."""
        debug = os.environ.get('DEBUG', '0') == '1'
        
        if not debug:  # Producción
            # Verificar variables de seguridad críticas
            security_vars = {
                'ALLOWED_HOSTS': os.environ.get('ALLOWED_HOSTS'),
                'SECURE_SSL_REDIRECT': os.environ.get('SECURE_SSL_REDIRECT'),
                'SESSION_COOKIE_SECURE': os.environ.get('SESSION_COOKIE_SECURE'),
                'CSRF_COOKIE_SECURE': os.environ.get('CSRF_COOKIE_SECURE'),
            }
            
            # ALLOWED_HOSTS debe estar configurado
            assert security_vars['ALLOWED_HOSTS'], \
                "ALLOWED_HOSTS debe estar configurado en producción"
    
    def test_feature_flags_are_boolean_strings(self):
        """Test que los feature flags usen valores booleanos válidos."""
        boolean_vars = [
            'DEBUG',
            'CORS_ALLOW_ALL_ORIGINS',
            'SECURE_SSL_REDIRECT',
            'SESSION_COOKIE_SECURE',
            'CSRF_COOKIE_SECURE',
            'FEATURE_LOT_OVERRIDE',
        ]
        
        valid_boolean_values = ['0', '1', 'true', 'false', 'True', 'False']
        
        for var in boolean_vars:
            value = os.environ.get(var)
            if value is not None:
                assert value in valid_boolean_values, \
                    f"{var} debe ser un valor booleano válido ({valid_boolean_values}), got: {value}"
    
    def test_numeric_variables_are_valid(self):
        """Test que las variables numéricas tengan valores válidos."""
        numeric_vars = {
            'CONN_MAX_AGE': (0, 3600),  # 0 a 1 hora
            'EMAIL_PORT': (1, 65535),   # Puertos válidos
            'LOW_STOCK_THRESHOLD_DEFAULT': (0, 1000),  # Threshold razonable
            'NEAR_EXPIRY_DAYS': (1, 365),  # 1 día a 1 año
            'JWT_ACCESS_TOKEN_LIFETIME_MINUTES': (1, 60),  # 1 a 60 minutos
            'JWT_REFRESH_TOKEN_LIFETIME_DAYS': (1, 30),    # 1 a 30 días
        }
        
        for var, (min_val, max_val) in numeric_vars.items():
            value = os.environ.get(var)
            if value is not None:
                try:
                    numeric_value = int(value)
                    assert min_val <= numeric_value <= max_val, \
                        f"{var} debe estar entre {min_val} y {max_val}, got: {numeric_value}"
                except ValueError:
                    pytest.fail(f"{var} debe ser un número válido, got: {value}")


class TestDatabaseConnectionSanity(TestCase):
    """Tests de sanidad para conexión a base de datos."""
    
    def test_database_connection_works(self):
        """Test que la conexión a la base de datos funcione."""
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.assertEqual(result[0], 1)
        except Exception as e:
            self.fail(f"No se pudo conectar a la base de datos: {e}")
    
    def test_database_migrations_are_applied(self):
        """Test que las migraciones estén aplicadas."""
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connection
        
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        self.assertEqual(len(plan), 0, 
                        f"Hay migraciones pendientes: {[migration.name for migration, _ in plan]}")


@pytest.mark.slow
class TestExternalServicesSanity:
    """Tests de sanidad para servicios externos (marcados como lentos)."""
    
    def test_redis_connection_if_configured(self):
        """Test conexión a Redis si está configurado."""
        redis_url = os.environ.get('REDIS_URL')
        
        if redis_url:
            try:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
            except ImportError:
                pytest.skip("Redis no está instalado")
            except (redis.ConnectionError, redis.TimeoutError):
                pytest.fail(f"No se pudo conectar a Redis: {redis_url}")
    
    def test_email_backend_if_smtp_configured(self):
        """Test backend de email si SMTP está configurado."""
        from django.core.mail import get_connection
        from django.conf import settings
        
        if 'smtp' in settings.EMAIL_BACKEND.lower():
            try:
                connection = get_connection()
                # Solo verificar que se puede crear la conexión
                # No enviar emails reales en tests
                assert connection is not None
            except Exception as e:
                pytest.fail(f"No se pudo crear conexión SMTP: {e}")