from django.db import models


class Product(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=160, db_index=True)
    brand = models.CharField(max_length=80, blank=True)
    unit = models.CharField(max_length=8, default="UN")
    category = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21)
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.code} - {self.name}"


class Benefit(models.Model):
    class Type(models.TextChoices):
        DISCOUNT = "discount", "Discount"
        COMBO = "combo", "Combo"

    class Segment(models.TextChoices):
        WHOLESALE = "wholesale", "Wholesale"
        RETAIL = "retail", "Retail"

    name = models.CharField(max_length=120)
    type = models.CharField(max_length=16, choices=Type.choices)
    segment = models.CharField(max_length=16, choices=Segment.choices)
    value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    combo_spec = models.JSONField(null=True, blank=True)
    active_from = models.DateField()
    active_to = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name
