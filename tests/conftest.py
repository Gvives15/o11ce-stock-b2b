"""
Configuración global de pytest y fixtures compartidas.
"""
import os
import pytest
import django
from django.conf import settings
from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.db import transaction
from unittest.mock import Mock, patch
import tempfile
import shutil
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone

# Configurar Django
# Asegurar que las pruebas no tomen la configuración de Docker/CI en entorno local
if os.environ.get('TESTING') != 'true':
    os.environ.pop('DATABASE_URL', None)
    os.environ.pop('POSTGRES_DB', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

# Importaciones después de configurar Django
from django.contrib.auth import get_user_model
from django.test import Client
from django.core.cache import cache

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup():
    """Configuración de base de datos para toda la sesión de tests.
    - En Docker/CI (DATABASE_URL o USE_TEST_DB=postgres), respeta la configuración de Postgres.
    - En entorno local, usa SQLite basada en archivo para evitar problemas de DB en memoria.
    """
    use_postgres = os.environ.get('USE_TEST_DB') == 'postgres' or bool(os.environ.get('DATABASE_URL'))
    if use_postgres:
        # Mantener configuración existente (PostgreSQL)
        return
    # Usar SQLite basada en archivo para evitar 'no such table' por DB en memoria
    tmp_db_path = os.path.join(tempfile.gettempdir(), 'pytest_db.sqlite3')
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': tmp_db_path,
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Permite acceso a la base de datos para todos los tests."""
    pass


@pytest.fixture
def client():
    """Cliente de Django para tests."""
    return Client()


@pytest.fixture
def admin_user(db):
    """Usuario administrador para tests."""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def regular_user(db):
    """Usuario regular para tests."""
    return User.objects.create_user(
        username='testuser',
        email='user@test.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, regular_user):
    """Cliente autenticado con usuario regular."""
    client.force_login(regular_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Cliente autenticado con usuario administrador."""
    client.force_login(admin_user)
    return client


@pytest.fixture
def temp_media_root():
    """Directorio temporal para archivos de media en tests."""
    temp_dir = tempfile.mkdtemp()
    with patch.object(settings, 'MEDIA_ROOT', temp_dir):
        yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_redis():
    """Mock de Redis para tests."""
    with patch('redis.Redis') as mock:
        yield mock


@pytest.fixture
def clear_cache():
    """Limpia el cache antes y después de cada test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def sample_product_data():
    """Datos de ejemplo para productos."""
    return {
        'name': 'Producto Test',
        'sku': 'TEST-001',
        'price': Decimal('10.99'),
        'cost': Decimal('5.50'),
        'stock_quantity': 100,
        'min_stock': 10,
        'max_stock': 500,
        'is_active': True,
        'category': 'test-category',
        'description': 'Producto de prueba para tests'
    }


@pytest.fixture
def sample_order_data():
    """Datos de ejemplo para órdenes."""
    return {
        'customer_name': 'Cliente Test',
        'customer_email': 'cliente@test.com',
        'total_amount': Decimal('25.99'),
        'status': 'pending',
        'created_at': timezone.now(),
        'items': [
            {
                'product_sku': 'TEST-001',
                'quantity': 2,
                'unit_price': Decimal('10.99')
            }
        ]
    }


@pytest.fixture
def sample_stock_movement_data():
    """Datos de ejemplo para movimientos de stock."""
    return {
        'product_sku': 'TEST-001',
        'movement_type': 'in',
        'quantity': 50,
        'reason': 'test_movement',
        'reference': 'TEST-REF-001',
        'created_at': timezone.now()
    }


@pytest.fixture
def expired_product_data():
    """Datos de producto con fecha de vencimiento para tests FEFO."""
    return {
        'name': 'Producto Perecedero',
        'sku': 'PERISHABLE-001',
        'price': Decimal('15.99'),
        'cost': Decimal('8.00'),
        'stock_quantity': 50,
        'expiry_date': timezone.now() + timedelta(days=30),
        'is_perishable': True,
        'batch_number': 'BATCH-001'
    }


@pytest.fixture
def mock_celery_task():
    """Mock para tareas de Celery."""
    with patch('celery.current_app.send_task') as mock:
        mock.return_value = Mock(id='test-task-id')
        yield mock


@pytest.fixture
def api_headers():
    """Headers estándar para tests de API."""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


@pytest.fixture
def performance_timer():
    """Timer para medir performance en tests."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = datetime.now()
        
        def stop(self):
            self.end_time = datetime.now()
            return (self.end_time - self.start_time).total_seconds()
    
    return Timer()


# Configuración de markers personalizados
def pytest_configure(config):
    """Configuración personalizada de pytest."""
    # Registrar markers personalizados
    config.addinivalue_line(
        "markers", "unit: Unit tests - fast, isolated tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - test component interactions"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests - full workflow tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "security: Security and vulnerability tests"
    )
    config.addinivalue_line(
        "markers", "fefo: FEFO (First Expired First Out) specific tests"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )
    config.addinivalue_line(
        "markers", "celery: Celery task tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests (>5 seconds)"
    )
    config.addinivalue_line(
        "markers", "django_db: Tests that require database access"
    )
    config.addinivalue_line(
        "markers", "redis: Tests that require Redis"
    )


def pytest_collection_modifyitems(config, items):
    """Modifica la colección de tests para agregar markers automáticamente."""
    for item in items:
        # Agregar marker django_db a tests que usan fixtures de DB
        if any(fixture in item.fixturenames for fixture in ['db', 'transactional_db', 'django_db_setup']):
            item.add_marker(pytest.mark.django_db)
        
        # Agregar marker slow a tests que pueden ser lentos
        if any(keyword in item.name.lower() for keyword in ['performance', 'load', 'stress', 'benchmark']):
            item.add_marker(pytest.mark.slow)
        
        # Agregar marker api a tests de API
        if any(keyword in item.name.lower() for keyword in ['api', 'endpoint', 'rest']):
            item.add_marker(pytest.mark.api)
        
        # Agregar marker fefo a tests relacionados con FEFO
        if any(keyword in item.name.lower() for keyword in ['fefo', 'expiry', 'expiration', 'fifo']):
            item.add_marker(pytest.mark.fefo)


@pytest.fixture(scope='session', autouse=True)
def apply_migrations(django_db_setup, django_db_blocker):
    """Aplica migraciones antes de ejecutar los tests para asegurar que las tablas existen.
    Usa django_db_blocker para permitir acceso a DB dentro de la sesión.
    """
    with django_db_blocker.unblock():
        call_command('migrate', run_syncdb=True, verbosity=0)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Configuración general del entorno de prueba (logging, tz, etc.)."""
    import logging
    # Reducir el ruido de logs en pruebas
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)