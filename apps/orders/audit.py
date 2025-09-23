"""
Modelo de auditoría para operaciones de entrega de órdenes.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from apps.orders.models import Order
from apps.stock.models import StockLot


class DeliveryAuditLog(models.Model):
    """
    Registro de auditoría para entregas de órdenes.
    Registra quién, cuándo y qué lotes/cantidades fueron entregados.
    """
    
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"
    
    # Información básica de la entrega
    order = models.ForeignKey(
        Order, 
        on_delete=models.PROTECT,
        db_index=True,
        help_text="Orden entregada"
    )
    
    # Actor y timestamp
    delivered_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        db_index=True,
        help_text="Usuario que realizó la entrega"
    )
    delivered_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Timestamp de la entrega"
    )
    
    # Estado de la entrega
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.SUCCESS,
        help_text="Estado de la entrega"
    )
    
    # Detalles de la entrega
    total_movements = models.PositiveIntegerField(
        help_text="Número total de movimientos creados"
    )
    
    # Información adicional
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notas adicionales sobre la entrega"
    )
    
    # Metadatos para debugging
    error_details = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles del error si la entrega falló"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['order', 'delivered_at'], name='idx_audit_order_date'),
            models.Index(fields=['delivered_by', 'delivered_at'], name='idx_audit_user_date'),
            models.Index(fields=['status', 'delivered_at'], name='idx_audit_status_date'),
        ]
        ordering = ['-delivered_at']
    
    def __str__(self) -> str:
        return f"Delivery #{self.id} · Order #{self.order_id} · {self.status} · {self.delivered_at}"


class DeliveryAuditLogItem(models.Model):
    """
    Detalle de cada lote entregado en una auditoría de entrega.
    """
    
    audit_log = models.ForeignKey(
        DeliveryAuditLog,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Registro de auditoría padre"
    )
    
    lot = models.ForeignKey(
        StockLot,
        on_delete=models.PROTECT,
        help_text="Lote entregado"
    )
    
    qty_delivered = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Cantidad entregada del lote"
    )
    
    movement_id = models.PositiveIntegerField(
        help_text="ID del movimiento EXIT creado"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['audit_log', 'lot'], name='idx_audit_item_log_lot'),
        ]
    
    def __str__(self) -> str:
        return f"AuditItem #{self.id} · Lot {self.lot.lot_code} · {self.qty_delivered}"