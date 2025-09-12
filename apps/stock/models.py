from django.conf import settings
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
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "lot_code", "warehouse"], name="uq_lot_per_product_warehouse"),
            models.CheckConstraint(check=Q(qty_on_hand__gte=0), name="ck_lot_qty_non_negative"),
        ]
        indexes = [models.Index(fields=["product", "expiry_date"], name="idx_lot_fefo")]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product_id}-{self.lot_code}"


class Movement(models.Model):
    class Type(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"

    type = models.CharField(max_length=8, choices=Type.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_index=True)
    lot = models.ForeignKey(StockLot, null=True, blank=True, on_delete=models.PROTECT, db_index=True)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=80, blank=True)
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(qty__gt=0), name="ck_movement_qty_positive"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.type} {self.product_id} {self.qty}"
