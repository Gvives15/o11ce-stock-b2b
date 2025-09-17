from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import hashlib
import json


class LotOverrideAudit(models.Model):
    """
    Modelo para auditoría de overrides de lotes en POS.
    Registra cada vez que se usa un override manual de lote.
    """
    # Actor que realizó el override
    actor = models.ForeignKey(User, on_delete=models.PROTECT, db_index=True)
    
    # Identificador único de la venta (sale_id del POS)
    sale_id = models.CharField(max_length=36, db_index=True, help_text="UUID de la venta POS")
    
    # Información del producto y lote
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, db_index=True)
    lot_chosen = models.ForeignKey('stock.StockLot', on_delete=models.PROTECT, db_index=True)
    
    # Cantidad del override
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    
    # Razón del override
    reason = models.TextField(help_text="Razón proporcionada para el override")
    
    # Timestamp del override
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['actor', 'timestamp'], name='idx_audit_actor_time'),
            models.Index(fields=['sale_id'], name='idx_audit_sale'),
            models.Index(fields=['product', 'timestamp'], name='idx_audit_prod_time'),
            models.Index(fields=['lot_chosen', 'timestamp'], name='idx_audit_lot_time'),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(qty__gt=0), name="ck_audit_qty_positive"),
        ]
    
    def __str__(self):
        return f"Override {self.sale_id[:8]} - {self.product.code} - {self.lot_chosen.lot_code}"


class SaleItemLot(models.Model):
    """
    Enlace entre items de venta y lotes consumidos para trazabilidad.
    Permite rastrear qué lotes y cantidades se usaron para cada ítem de una venta.
    """
    # Identificador único de la venta (sale_id del POS)
    sale_id = models.CharField(max_length=36, db_index=True, help_text="UUID de la venta POS")
    
    # Posición del ítem en la venta (1, 2, 3...)
    item_sequence = models.PositiveIntegerField(help_text="Posición del ítem en la venta")
    
    # Información del producto y lote
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, db_index=True)
    lot = models.ForeignKey('stock.StockLot', on_delete=models.PROTECT, db_index=True)
    
    # Cantidad consumida de este lote para este ítem
    qty_consumed = models.DecimalField(max_digits=12, decimal_places=3)
    
    # Precio unitario del ítem (para cálculos)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Referencia al movimiento de stock asociado
    movement = models.ForeignKey('stock.Movement', on_delete=models.PROTECT, db_index=True)
    
    # Timestamp de creación
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['sale_id'], name='idx_sale_item_lot_sale'),
            models.Index(fields=['sale_id', 'item_sequence'], name='idx_sale_item_lot_item'),
            models.Index(fields=['product', 'created_at'], name='idx_sale_item_lot_prod_date'),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(qty_consumed__gt=0), name="ck_sale_item_lot_qty_positive"),
            models.CheckConstraint(check=models.Q(item_sequence__gt=0), name="ck_sale_item_lot_sequence_positive"),
        ]

    def __str__(self):
        return f"Sale {self.sale_id[:8]} - Item {self.item_sequence} - {self.lot.lot_code}"


class SaleIdempotencyKey(models.Model):
    """
    Modelo para manejar idempotencia en ventas POS.
    Evita duplicados usando Idempotency-Key en headers HTTP.
    """
    
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
    
    # Clave de idempotencia proporcionada por el cliente
    idempotency_key = models.CharField(max_length=255, db_index=True)
    
    # Usuario que realizó la operación
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # ID de la venta generada (si se completó exitosamente)
    sale_id = models.CharField(max_length=36, null=True, blank=True)
    
    # Hash del request para verificar consistencia
    request_hash = models.CharField(max_length=64)
    
    # Estado de la operación
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING
    )
    
    # Respuesta guardada para devolver en requests duplicados
    response_data = models.JSONField(null=True, blank=True)
    
    # Mensaje de error si falló
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['idempotency_key', 'user'], name='pos_saleide_idempot_8ff7eb_idx'),
            models.Index(fields=['expires_at'], name='pos_saleide_expires_36b674_idx'),
            models.Index(fields=['created_at'], name='pos_saleide_created_644996_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('idempotency_key', 'user'),
                name='unique_idempotency_per_user'
            )
        ]
    
    @classmethod
    def create_hash(cls, request_data):
        """Crea un hash del request para verificar consistencia."""
        # Convertir a JSON ordenado para hash consistente
        json_str = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    @classmethod
    def get_expiry_time(cls):
        """Calcula tiempo de expiración (24 horas desde ahora)."""
        return timezone.now() + timedelta(hours=24)
    
    def is_expired(self):
        """Verifica si la clave de idempotencia ha expirado."""
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"Idempotency {self.idempotency_key[:8]} - {self.user.username} - {self.status}"
