from django.db import models
from django.db.models import Q

from apps.orders.models import Order
from apps.stock.models import StockLot


class Reservation(models.Model):
    """
    Modelo para reservas de lotes específicos para órdenes.
    Permite separar la reserva de stock de la entrega física.
    """
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPLIED = "applied", "Applied"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="Orden para la cual se reserva el stock"
    )
    lot = models.ForeignKey(
        StockLot, 
        on_delete=models.PROTECT, 
        db_index=True,
        help_text="Lote específico reservado"
    )
    qty = models.DecimalField(
        max_digits=12, 
        decimal_places=3,
        help_text="Cantidad reservada del lote"
    )
    status = models.CharField(
        max_length=12, 
        choices=Status.choices, 
        default=Status.PENDING,
        help_text="Estado de la reserva"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Cantidad debe ser positiva
            models.CheckConstraint(
                check=Q(qty__gt=0), 
                name="ck_reservation_qty_positive"
            ),
            # Una reserva por orden-lote (evita duplicados)
            models.UniqueConstraint(
                fields=["order", "lot"], 
                name="uq_reservation_order_lot"
            ),
        ]
        
        indexes = [
            # Índice para consultas por orden (picking suggestions)
            models.Index(
                fields=["order", "status"], 
                name="idx_reservation_order_status"
            ),
            # Índice para consultas por lote (disponibilidad)
            models.Index(
                fields=["lot", "status"], 
                name="idx_reservation_lot_status"
            ),
            # Índice compuesto para queries de disponibilidad
            models.Index(
                fields=["lot", "status", "qty"], 
                name="idx_reservation_availability"
            ),
            # Índice temporal para auditoría
            models.Index(
                fields=["created_at"], 
                name="idx_reservation_created"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Reservation #{self.id} · Order #{self.order_id} · Lot {self.lot.lot_code} · {self.qty}"

    @property
    def is_active(self) -> bool:
        """Indica si la reserva está activa (pending o applied)"""
        return self.status in [self.Status.PENDING, self.Status.APPLIED]

    def cancel(self):
        """Cancela la reserva"""
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    def apply(self):
        """Marca la reserva como aplicada (entregada)"""
        self.status = self.Status.APPLIED
        self.save(update_fields=['status', 'updated_at'])