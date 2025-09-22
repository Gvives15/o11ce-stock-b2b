"""
Cache service for performance optimization.
Provides caching utilities with metrics tracking.
"""

from django.core.cache import cache
from django.conf import settings
from django.http import HttpRequest
import hashlib
import json
from typing import Any, Optional, Dict
from prometheus_client import Counter, Histogram
import time

# Métricas de cache
cache_hits_total = Counter('cache_hits_total', 'Total cache hits', ['endpoint'])
cache_misses_total = Counter('cache_misses_total', 'Total cache misses', ['endpoint'])
cache_operation_duration = Histogram('cache_operation_duration_seconds', 'Cache operation duration', ['operation'])

class CacheService:
    """Service for managing cache operations with metrics."""
    
    @staticmethod
    def generate_cache_key(prefix: str, **kwargs) -> str:
        """Generate a consistent cache key from parameters."""
        # Crear un hash de los parámetros para evitar claves muy largas
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{prefix}:{params_hash}"
    
    @staticmethod
    def get_cached_response(cache_key: str, endpoint: str) -> Optional[Any]:
        """Get cached response and track metrics."""
        start_time = time.time()
        try:
            result = cache.get(cache_key)
            if result is not None:
                cache_hits_total.labels(endpoint=endpoint).inc()
                return result
            else:
                cache_misses_total.labels(endpoint=endpoint).inc()
                return None
        finally:
            cache_operation_duration.labels(operation='get').observe(time.time() - start_time)
    
    @staticmethod
    def set_cached_response(cache_key: str, data: Any, timeout: int = 300) -> None:
        """Set cached response with timeout."""
        start_time = time.time()
        try:
            cache.set(cache_key, data, timeout)
        finally:
            cache_operation_duration.labels(operation='set').observe(time.time() - start_time)
    
    @staticmethod
    def invalidate_pattern(pattern: str) -> None:
        """Invalidate cache keys matching a pattern."""
        start_time = time.time()
        try:
            # Django-redis supports pattern deletion
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(f"*{pattern}*")
            else:
                # Fallback for other cache backends
                cache.clear()
        finally:
            cache_operation_duration.labels(operation='invalidate').observe(time.time() - start_time)

def cache_response(timeout: int = 300, key_prefix: str = "api"):
    """
    Decorator for caching API responses.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(func):
        def wrapper(request: HttpRequest, *args, **kwargs):
            # Para Django Ninja, los parámetros vienen en kwargs
            # Incluir tanto args como kwargs en la clave de cache
            import inspect
            
            # Obtener los parámetros de la función
            sig = inspect.signature(func)
            bound_args = sig.bind(request, *args, **kwargs)
            bound_args.apply_defaults()
            
            # Crear parámetros de cache incluyendo todos los argumentos
            cache_params = {
                'func': func.__name__,
                'args': dict(bound_args.arguments)
            }
            
            # Remover el request de los parámetros de cache
            if 'request' in cache_params['args']:
                del cache_params['args']['request']
            
            cache_key = CacheService.generate_cache_key(key_prefix, **cache_params)
            endpoint = f"{key_prefix}_{func.__name__}"
            
            # Intentar obtener de cache
            cached_result = CacheService.get_cached_response(cache_key, endpoint)
            if cached_result is not None:
                return cached_result
            
            # Ejecutar función y cachear resultado
            result = func(request, *args, **kwargs)
            CacheService.set_cached_response(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator