from django.db import models
from django.db.models import Q

from apps.customers.models import Customer
from apps.catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLACED = "placed", "Placed"

    class DeliveryMethod(models.TextChoices):
        DELIVERY = "delivery", "Delivery"
        PICKUP = "pickup", "Pickup"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    currency = models.CharField(max_length=3, default="ARS")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    delivery_method = models.CharField(max_length=8, choices=DeliveryMethod.choices)
    delivery_address_text = models.CharField(max_length=255, blank=True)
    delivery_window_from = models.TimeField(null=True, blank=True)
    delivery_window_to = models.TimeField(null=True, blank=True)
    delivery_instructions = models.TextField(blank=True)
    requested_delivery_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Order {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_index=True)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    benefit_applied = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="uq_orderitem_per_product"),
            models.CheckConstraint(check=Q(qty__gt=0), name="ck_orderitem_qty_positive"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product_id} x {self.qty}"
