from django.db import models


class Order(models.Model):
    """Represents a customer's order."""

    STATUS_PENDING = "pending"
    STATUS_SHIPPED = "shipped"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    customer = models.ForeignKey(
        "customers.Customer",
        related_name="orders",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Order {self.pk}"


class OrderItem(models.Model):
    """Line item within an order."""

    order = models.ForeignKey(
        Order, related_name="items", on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        "catalog.Product", related_name="order_items", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.product} x {self.quantity}"

