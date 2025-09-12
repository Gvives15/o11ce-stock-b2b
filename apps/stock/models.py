from django.db import models


class Warehouse(models.Model):
    """Represents a storage location."""

    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name


class StockItem(models.Model):
    """Quantifies product availability in a warehouse."""

    product = models.ForeignKey(
        "catalog.Product",
        related_name="stock_items",
        on_delete=models.CASCADE,
    )
    warehouse = models.ForeignKey(
        Warehouse,
        related_name="stock_items",
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "warehouse")

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.product} @ {self.warehouse}"

