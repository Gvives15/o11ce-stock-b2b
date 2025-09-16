from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


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
