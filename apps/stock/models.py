from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.catalog.models import Product


class Warehouse(models.Model):
    name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class StockLot(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_index=True)
    lot_code = models.CharField(max_length=40)
    expiry_date = models.DateField(db_index=True)
    qty_on_hand = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    warehouse = models.ForeignKey(Warehouse, null=False, on_delete=models.PROTECT)  # Siempre requerido
    is_quarantined = models.BooleanField(default=False, help_text="Lote en cuarentena, no disponible para venta")
    is_reserved = models.BooleanField(default=False, help_text="Lote reservado, no disponible para asignación automática")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "lot_code", "warehouse"], name="uq_lot_per_product_warehouse"),
            models.CheckConstraint(check=Q(qty_on_hand__gte=0), name="ck_lot_qty_non_negative"),
            models.CheckConstraint(check=Q(unit_cost__gt=0), name="ck_lot_unit_cost_positive"),  # Nuevo: unit_cost > 0
        ]
        indexes = [
            models.Index(fields=["product", "expiry_date"], name="idx_lot_fefo"),
            # Nuevo: índice compuesto para FEFO optimizado
            models.Index(fields=["product", "warehouse", "is_quarantined", "is_reserved", "expiry_date"], 
                        name="idx_lot_fefo_pick"),
        ]

    @property
    def qty_available(self):
        """Cantidad disponible para asignación considerando reservas activas"""
        if self.is_quarantined or self.is_reserved:
            return 0
        
        # Verificar si el lote está vencido
        from datetime import date
        if self.expiry_date < date.today():
            return 0
        
        # Calcular reservas activas para este lote
        from apps.stock.reservations import Reservation
        active_reservations = Reservation.objects.filter(
            lot=self,
            status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
        ).aggregate(
            total_reserved=models.Sum('qty')
        )['total_reserved'] or 0
        
        # Disponible = on_hand - reservas activas
        available = self.qty_on_hand - active_reservations
        return max(0, available)  # No puede ser negativo

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product_id}-{self.lot_code}"


class Movement(models.Model):
    class Type(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"

    class Reason(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURN_CUSTOMER = "return_customer", "Return from Customer"
        RETURN_SUPPLIER = "return_supplier", "Return to Supplier"
        TRANSFER = "transfer", "Transfer"
        DAMAGE = "damage", "Damage"
        EXPIRY = "expiry", "Expiry"

    type = models.CharField(max_length=8, choices=Type.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_index=True)
    lot = models.ForeignKey(StockLot, null=True, blank=True, on_delete=models.PROTECT, db_index=True)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.ADJUSTMENT)
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(qty__gt=0), name="ck_movement_qty_positive"),
            # Nuevos constraints condicionales para ENTRY
            models.CheckConstraint(
                check=(
                    Q(type='exit') |  # Si es EXIT, no aplica
                    (Q(type='entry') & Q(lot__isnull=False) & Q(unit_cost__isnull=False) & Q(unit_cost__gt=0))
                ),
                name="ck_movement_entry_requires_lot_and_cost"
            ),
            # Nuevo constraint condicional para EXIT
            models.CheckConstraint(
                check=(
                    Q(type='entry') |  # Si es ENTRY, no aplica
                    (Q(type='exit') & Q(lot__isnull=False))
                ),
                name="ck_movement_exit_requires_lot"
            ),
        ]
        indexes = [
            models.Index(fields=['product', 'created_at'], name='idx_movement_product_date'),
            models.Index(fields=['type', 'created_at'], name='idx_movement_type_date'),
        ]

    def clean(self):
        """Validación de consistencia: Movement.product debe coincidir con Movement.lot.product"""
        super().clean()
        if self.lot and self.product_id != self.lot.product_id:
            raise ValidationError({
                'lot': f'El lote pertenece al producto {self.lot.product.code}, pero el movimiento es para {self.product.code}'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.type.title()} · {self.product.code} · {self.qty}"


# Import Reservation model to make it available in the stock app
from .reservations import Reservation

__all__ = ['Warehouse', 'StockLot', 'Movement', 'Reservation']
