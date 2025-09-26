# apps/stock/idempotency_service.py
"""Service for handling idempotency keys in stock operations."""

import hashlib
import json
from datetime import timedelta
from typing import Optional, Dict, Any, Tuple

from django.utils import timezone
from django.db import transaction
from django.http import HttpRequest

from .models_idempotency import StockIdempotencyKey


class IdempotencyService:
    """Service for managing idempotency keys in stock operations."""
    
    # Default TTL for idempotency keys (24 hours)
    DEFAULT_TTL_HOURS = 24
    
    @staticmethod
    def get_idempotency_key(request: HttpRequest) -> Optional[str]:
        """Extract idempotency key from request headers."""
        return request.headers.get('Idempotency-Key')
    
    @staticmethod
    def _hash_request_data(data: Dict[str, Any]) -> str:
        """Create a hash of the request data for validation."""
        # Sort keys to ensure consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    @classmethod
    def check_existing_request(
        self, 
        key: str, 
        operation_type: str, 
        request_data: Dict[str, Any]
    ) -> Optional[Tuple[int, Dict[str, Any]]]:
        """
        Check if this idempotency key was already processed.
        
        Returns:
            Tuple of (status_code, response_data) if found, None otherwise
            
        Raises:
            ValueError: If key exists but request data doesn't match
        """
        try:
            existing = StockIdempotencyKey.objects.get(key=key)
            
            # Check if expired
            if existing.is_expired():
                # Clean up expired key
                existing.delete()
                return None
            
            # Validate operation type matches
            if existing.operation_type != operation_type:
                raise ValueError(
                    f"Idempotency key '{key}' was used for {existing.operation_type}, "
                    f"but current request is for {operation_type}"
                )
            
            # Validate request data matches
            request_hash = self._hash_request_data(request_data)
            if existing.request_hash != request_hash:
                raise ValueError(
                    f"Idempotency key '{key}' was used with different request data"
                )
            
            # Return cached response
            return existing.status_code, existing.response_data
            
        except StockIdempotencyKey.DoesNotExist:
            return None
    
    @classmethod
    def store_response(
        self,
        key: str,
        operation_type: str,
        request_data: Dict[str, Any],
        status_code: int,
        response_data: Dict[str, Any],
        created_by=None,
        ttl_hours: Optional[int] = None
    ) -> StockIdempotencyKey:
        """
        Store the response for this idempotency key.
        
        Args:
            key: The idempotency key
            operation_type: Type of operation (entry/exit)
            request_data: Original request payload
            status_code: HTTP status code of response
            response_data: Response data to cache
            created_by: User who made the request
            ttl_hours: Hours until key expires (default: 24)
        """
        ttl_hours = ttl_hours or self.DEFAULT_TTL_HOURS
        expires_at = timezone.now() + timedelta(hours=ttl_hours)
        request_hash = self._hash_request_data(request_data)
        
        with transaction.atomic():
            # Use get_or_create to handle race conditions
            idempotency_record, created = StockIdempotencyKey.objects.get_or_create(
                key=key,
                defaults={
                    'operation_type': operation_type,
                    'request_hash': request_hash,
                    'response_data': response_data,
                    'status_code': status_code,
                    'created_by': created_by,
                    'expires_at': expires_at,
                }
            )
            
            if not created:
                # Key already exists - validate it matches
                if idempotency_record.request_hash != request_hash:
                    raise ValueError(
                        f"Idempotency key '{key}' already exists with different request data"
                    )
                if idempotency_record.operation_type != operation_type:
                    raise ValueError(
                        f"Idempotency key '{key}' already exists for different operation type"
                    )
            
            return idempotency_record
    
    @classmethod
    def cleanup_expired_keys(cls, batch_size: int = 1000) -> int:
        """
        Clean up expired idempotency keys.
        
        Returns:
            Number of keys deleted
        """
        now = timezone.now()
        expired_keys = StockIdempotencyKey.objects.filter(
            expires_at__lt=now
        )[:batch_size]
        
        count = len(expired_keys)
        if count > 0:
            StockIdempotencyKey.objects.filter(
                id__in=[key.id for key in expired_keys]
            ).delete()
        
        return count