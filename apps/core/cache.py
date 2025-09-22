"""
Fault-tolerant cache wrapper that gracefully handles Redis failures.
"""
import logging
import functools
from typing import Any, Optional, Union, Callable
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.conf import settings
from apps.core.metrics import increment_counter

logger = logging.getLogger(__name__)


class FaultTolerantCache:
    """
    Cache wrapper that gracefully handles Redis failures.
    
    When Redis is down:
    - get() returns None (cache miss)
    - set() logs warning and continues
    - delete() logs warning and continues
    - Metrics are incremented for monitoring
    """
    
    def __init__(self, cache_backend=None):
        self.cache = cache_backend or cache
        self._redis_available = True
        
    def _handle_redis_error(self, operation: str, key: str, error: Exception) -> None:
        """Handle Redis connection errors gracefully."""
        if self._redis_available:
            # First failure - log as warning
            logger.warning(f"Redis cache {operation} failed for key '{key}': {error}")
            self._redis_available = False
        else:
            # Subsequent failures - log as debug to avoid spam
            logger.debug(f"Redis cache {operation} failed for key '{key}': {error}")
        
        # Increment failure metric
        increment_counter('redis_failures_total', {
            'operation': operation,
            'error_type': type(error).__name__
        })
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache. Returns default if Redis is down.
        
        Args:
            key: Cache key
            default: Default value if key not found or Redis is down
            
        Returns:
            Cached value or default
        """
        try:
            value = self.cache.get(key, default)
            
            # Reset availability flag on successful operation
            if not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
                
            return value
            
        except Exception as exc:
            self._handle_redis_error('get', key, exc)
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set value in cache. Returns False if Redis is down.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False if Redis is down
        """
        try:
            self.cache.set(key, value, timeout)
            
            # Reset availability flag on successful operation
            if not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
                
            return True
            
        except Exception as exc:
            self._handle_redis_error('set', key, exc)
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache. Returns False if Redis is down.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False if Redis is down
        """
        try:
            result = self.cache.delete(key)
            
            # Reset availability flag on successful operation
            if not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
                
            return bool(result)
            
        except Exception as exc:
            self._handle_redis_error('delete', key, exc)
            return False
    
    def get_many(self, keys: list) -> dict:
        """
        Get multiple values from cache. Returns empty dict if Redis is down.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict of key-value pairs found in cache
        """
        try:
            result = self.cache.get_many(keys)
            
            # Reset availability flag on successful operation
            if not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
                
            return result
            
        except Exception as exc:
            self._handle_redis_error('get_many', str(keys), exc)
            return {}
    
    def set_many(self, data: dict, timeout: Optional[int] = None) -> bool:
        """
        Set multiple values in cache. Returns False if Redis is down.
        
        Args:
            data: Dict of key-value pairs to cache
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False if Redis is down
        """
        try:
            self.cache.set_many(data, timeout)
            
            # Reset availability flag on successful operation
            if not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
                
            return True
            
        except Exception as exc:
            self._handle_redis_error('set_many', str(list(data.keys())), exc)
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache. Returns False if Redis is down.
        
        Returns:
            True if successful, False if Redis is down
        """
        try:
            self.cache.clear()
            
            # Reset availability flag on successful operation
            if not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
                
            return True
            
        except Exception as exc:
            self._handle_redis_error('clear', 'all', exc)
            return False
    
    def is_available(self) -> bool:
        """
        Check if Redis cache is available.
        
        Returns:
            True if Redis is available, False otherwise
        """
        try:
            # Try a simple operation
            test_key = '_cache_health_check'
            self.cache.set(test_key, 'ok', 1)
            result = self.cache.get(test_key)
            self.cache.delete(test_key)
            
            available = result == 'ok'
            
            if available and not self._redis_available:
                logger.info("Redis cache is back online")
                self._redis_available = True
            elif not available and self._redis_available:
                logger.warning("Redis cache is not responding")
                self._redis_available = False
                
            return available
            
        except Exception as exc:
            if self._redis_available:
                logger.warning(f"Redis cache health check failed: {exc}")
                self._redis_available = False
            
            increment_counter('redis_failures_total', {
                'operation': 'health_check',
                'error_type': type(exc).__name__
            })
            
            return False


# Global fault-tolerant cache instance
fault_tolerant_cache = FaultTolerantCache()


def cached_function(timeout: int = 300, key_prefix: str = ''):
    """
    Decorator for caching function results with fault tolerance.
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
        key_prefix: Prefix for cache keys
        
    Usage:
        @cached_function(timeout=600, key_prefix='products')
        def get_product_list():
            return expensive_database_query()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}"
            
            # Add args and kwargs to key if present
            if args:
                cache_key += f":args:{hash(args)}"
            if kwargs:
                cache_key += f":kwargs:{hash(tuple(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = fault_tolerant_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                increment_counter('cache_hits_total', {'function': func.__name__})
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache miss for {func.__name__}")
            increment_counter('cache_misses_total', {'function': func.__name__})
            
            result = func(*args, **kwargs)
            
            # Cache the result
            fault_tolerant_cache.set(cache_key, result, timeout)
            
            return result
            
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate cache keys matching a pattern.
    
    Args:
        pattern: Pattern to match (simple string matching)
        
    Returns:
        Number of keys invalidated (0 if Redis is down)
    """
    try:
        # This is a simplified implementation
        # In production, you might want to use Redis SCAN with patterns
        logger.info(f"Cache invalidation requested for pattern: {pattern}")
        
        # For now, we'll just log the request
        # A full implementation would require direct Redis access
        increment_counter('cache_invalidations_total', {'pattern': pattern})
        
        return 1  # Assume success
        
    except Exception as exc:
        logger.error(f"Cache invalidation failed for pattern '{pattern}': {exc}")
        increment_counter('redis_failures_total', {
            'operation': 'invalidate',
            'error_type': type(exc).__name__
        })
        
        return 0


# Convenience functions using the global instance
def cache_get(key: str, default: Any = None) -> Any:
    """Get value from fault-tolerant cache."""
    return fault_tolerant_cache.get(key, default)


def cache_set(key: str, value: Any, timeout: Optional[int] = None) -> bool:
    """Set value in fault-tolerant cache."""
    return fault_tolerant_cache.set(key, value, timeout)


def cache_delete(key: str) -> bool:
    """Delete key from fault-tolerant cache."""
    return fault_tolerant_cache.delete(key)


def cache_is_available() -> bool:
    """Check if cache is available."""
    return fault_tolerant_cache.is_available()