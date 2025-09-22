"""
Health checks para observabilidad del sistema.
"""
import time
import structlog
from django.db import connection
from django.core.cache import cache
from django.core.mail import get_connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


logger = structlog.get_logger(__name__)


def check_database():
    """Verificar conectividad con la base de datos."""
    try:
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            'status': 'healthy',
            'latency_ms': latency_ms,
            'details': 'Database connection successful'
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            'status': 'unhealthy',
            'error': str(e),
            'details': 'Database connection failed'
        }


def check_cache():
    """Verificar conectividad con Redis/Cache usando wrapper tolerante a fallos."""
    try:
        from apps.core.cache import fault_tolerant_cache
        
        start_time = time.time()
        test_key = 'health_check_test'
        test_value = 'ok'
        
        # Test write
        write_success = fault_tolerant_cache.set(test_key, test_value, timeout=10)
        
        # Test read
        cached_value = fault_tolerant_cache.get(test_key)
        
        # Cleanup
        fault_tolerant_cache.delete(test_key)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Check if cache is available
        is_available = fault_tolerant_cache.is_available()
        
        if is_available and cached_value == test_value:
            return {
                'status': 'healthy',
                'latency_ms': latency_ms,
                'details': 'Cache read/write successful',
                'fault_tolerant': True
            }
        elif write_success and cached_value != test_value:
            return {
                'status': 'degraded',
                'latency_ms': latency_ms,
                'details': 'Cache write succeeded but read failed',
                'fault_tolerant': True
            }
        else:
            return {
                'status': 'degraded',
                'latency_ms': latency_ms,
                'details': 'Cache unavailable but application continues (fault-tolerant)',
                'fault_tolerant': True,
                'redis_available': False
            }
    except Exception as e:
        logger.error("Cache health check failed", error=str(e))
        return {
            'status': 'degraded',
            'error': str(e),
            'details': 'Cache connection failed but application continues (fault-tolerant)',
            'fault_tolerant': True
        }


def check_smtp():
    """Verificar conectividad con el servidor SMTP con timeout."""
    try:
        import socket
        from django.core.mail import get_connection
        
        start_time = time.time()
        
        # Set socket timeout for SMTP connection (3-5 seconds as per requirements)
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(4.0)  # 4 seconds timeout
        
        try:
            connection = get_connection()
            connection.open()
            connection.close()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                'status': 'healthy',
                'latency_ms': latency_ms,
                'details': 'SMTP connection successful',
                'timeout_configured': True,
                'timeout_seconds': 4.0
            }
            
        finally:
            # Restore original timeout
            socket.setdefaulttimeout(original_timeout)
        
    except socket.timeout:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning("SMTP health check timed out")
        return {
            'status': 'unhealthy',
            'latency_ms': latency_ms,
            'error': 'Connection timeout',
            'details': 'SMTP connection timed out after 4 seconds',
            'timeout_configured': True,
            'timeout_seconds': 4.0
        }
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error("SMTP health check failed", error=str(e))
        return {
            'status': 'unhealthy',
            'latency_ms': latency_ms,
            'error': str(e),
            'details': 'SMTP connection failed',
            'timeout_configured': True,
            'timeout_seconds': 4.0
        }


def check_celery():
    """Verificar estado de Celery workers y broker."""
    try:
        from celery import current_app
        from kombu import Connection
        import socket
        
        start_time = time.time()
        
        # Check broker connection (Redis)
        try:
            broker_url = current_app.conf.broker_url
            with Connection(broker_url) as conn:
                conn.ensure_connection(max_retries=1)
            broker_status = 'healthy'
            broker_error = None
        except Exception as e:
            broker_status = 'unhealthy'
            broker_error = str(e)
        
        # Check active workers
        try:
            inspect = current_app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                worker_count = len(active_workers)
                worker_status = 'healthy'
                worker_error = None
            else:
                worker_count = 0
                worker_status = 'unhealthy'
                worker_error = 'No active workers found'
                
        except Exception as e:
            worker_count = 0
            worker_status = 'unhealthy'
            worker_error = str(e)
        
        # Check scheduled tasks (Beat)
        try:
            scheduled_tasks = current_app.control.inspect().scheduled()
            beat_status = 'healthy' if scheduled_tasks is not None else 'unknown'
            beat_error = None
        except Exception as e:
            beat_status = 'unhealthy'
            beat_error = str(e)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Overall Celery status
        if broker_status == 'healthy' and worker_status == 'healthy':
            overall_status = 'healthy'
            details = f'Celery operational: {worker_count} workers active'
        elif broker_status == 'healthy' and worker_count == 0:
            overall_status = 'degraded'
            details = 'Broker healthy but no workers active'
        else:
            overall_status = 'unhealthy'
            details = 'Celery broker or workers unavailable'
        
        return {
            'status': overall_status,
            'latency_ms': latency_ms,
            'details': details,
            'components': {
                'broker': {
                    'status': broker_status,
                    'error': broker_error
                },
                'workers': {
                    'status': worker_status,
                    'count': worker_count,
                    'error': worker_error
                },
                'beat': {
                    'status': beat_status,
                    'error': beat_error
                }
            }
        }
        
    except ImportError:
        return {
            'status': 'not_configured',
            'details': 'Celery not installed or configured'
        }
    except Exception as e:
        logger.error("Celery health check failed", error=str(e))
        return {
            'status': 'unhealthy',
            'error': str(e),
            'details': 'Celery check failed'
        }


@csrf_exempt
@require_http_methods(["GET"])
def health_live(request):
    """
    Endpoint de liveness probe.
    Verifica que la aplicación esté corriendo y pueda responder requests.
    """
    start_time = time.time()
    
    response_data = {
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'bff-stock-system',
        'version': '1.0.0',
        'uptime_check': 'ok'
    }
    
    latency_ms = int((time.time() - start_time) * 1000)
    response_data['latency_ms'] = latency_ms
    
    logger.info(
        "health_live_check",
        status="healthy",
        latency_ms=latency_ms
    )
    
    return JsonResponse(response_data, status=200)


@csrf_exempt
@require_http_methods(["GET"])
def health_ready(request):
    """
    Endpoint de readiness probe.
    Verifica que la aplicación esté lista para recibir tráfico
    (DB, cache, servicios externos funcionando).
    """
    start_time = time.time()
    
    # Ejecutar todos los health checks
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'smtp': check_smtp(),
        'celery': check_celery(),
    }
    
    # Determinar estado general
    overall_status = 'healthy'
    failed_checks = []
    
    for service, check_result in checks.items():
        if check_result['status'] == 'unhealthy':
            overall_status = 'unhealthy'
            failed_checks.append(service)
    
    # Calcular latencia total
    total_latency_ms = int((time.time() - start_time) * 1000)
    
    response_data = {
        'status': overall_status,
        'timestamp': time.time(),
        'service': 'bff-stock-system',
        'version': '1.0.0',
        'checks': checks,
        'failed_checks': failed_checks,
        'latency_ms': total_latency_ms
    }
    
    # Determinar código de respuesta HTTP
    status_code = 200 if overall_status == 'healthy' else 503
    
    logger.info(
        "health_ready_check",
        status=overall_status,
        failed_checks=failed_checks,
        latency_ms=total_latency_ms
    )
    
    return JsonResponse(response_data, status=status_code)