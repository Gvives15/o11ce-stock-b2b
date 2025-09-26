# apps/stock/models_idempotency.py
"""Models for idempotency key handling in stock operations."""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class StockIdempotencyKey(models.Model):
    """
    Stores idempotency keys for stock operations to prevent duplicate requests.
    
    Each key is unique and stores the response data for the original request.
    This allows returning the same response for duplicate requests.
    """
    
    class OperationType(models.TextChoices):
        ENTRY = "entry", "Stock Entry"
        EXIT = "exit", "Stock Exit"
    
    key = models.CharField(max_length=128, unique=True, db_index=True)
    operation_type = models.CharField(max_length=10, choices=OperationType.choices)
    
    # Store the original request data for validation
    request_hash = models.CharField(max_length=64, help_text="Hash of request payload")
    
    # Store the response data to return for duplicate requests
    response_data = models.JSONField(help_text="Original response data")
    status_code = models.IntegerField(help_text="HTTP status code of original response")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: TTL for cleanup (could be handled by a cleanup job)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When this key expires")
    
    class Meta:
        db_table = 'stock_idempotency_keys'
        indexes = [
            models.Index(fields=['operation_type', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(status_code__gte=200) & models.Q(status_code__lt=600),
                name='ck_stock_idempotency_valid_status_code'
            )
        ]
    
    def __str__(self):
        return f"{self.operation_type}:{self.key[:16]}..."
    
    def is_expired(self):
        """Check if this idempotency key has expired."""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at