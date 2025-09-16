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
    
    # Idempotencia simple
    client_req_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(subtotal__gte=0), 
                name="ck_order_subtotal_non_negative"
            ),
            models.CheckConstraint(
                check=Q(discount_total__gte=0), 
                name="ck_order_discount_non_negative"
            ),
            models.CheckConstraint(
                check=Q(tax_total__gte=0), 
                name="ck_order_tax_non_negative"
            ),
            models.CheckConstraint(
                check=Q(total__gte=0), 
                name="ck_order_total_non_negative"
            ),
            models.CheckConstraint(
                check=Q(delivery_window_to__gte=models.F('delivery_window_from')) | Q(delivery_window_from__isnull=True) | Q(delivery_window_to__isnull=True), 
                name="ck_order_valid_delivery_window"
            ),
            models.UniqueConstraint(
                fields=['client_req_id'],
                condition=Q(client_req_id__isnull=False),
                name='uq_order_client_req_id'
            ),
        ]
        indexes = [
            models.Index(fields=['customer', 'status'], name='idx_order_customer_status'),
            models.Index(fields=['status', 'created_at'], name='idx_order_status_date'),
            models.Index(fields=['requested_delivery_date'], name='idx_order_delivery_date'),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Order #{self.id} · {self.customer.name}"


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
            models.CheckConstraint(check=Q(unit_price__gte=0), name="ck_orderitem_price_non_negative"),
        ]
        indexes = [
            models.Index(fields=['order'], name='idx_orderitem_order'),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product.code} × {self.qty}"
