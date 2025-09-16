from django.db import models
from django.db.models import Q


class Product(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=160, db_index=True)
    brand = models.CharField(max_length=80, blank=True)
    unit = models.CharField(max_length=8, default="UN")  # UN/KG/LT
    category = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21)  # %
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(price__gt=0), 
                name="ck_product_price_positive"
            ),
            models.CheckConstraint(
                check=Q(tax_rate__gte=0), 
                name="ck_product_tax_rate_non_negative"
            ),
        ]
        indexes = [
            models.Index(fields=['is_active', 'category'], name='idx_product_active_category'),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.code} · {self.name}"


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
    value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # porcentaje
    combo_spec = models.JSONField(null=True, blank=True)  # p.ej. {"sku":"CHOC90","x":3,"pay":2}
    active_from = models.DateField()
    active_to = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(active_to__gte=models.F('active_from')), 
                name="ck_benefit_valid_date_range"
            ),
            models.CheckConstraint(
                check=Q(value__gte=0) | Q(value__isnull=True), 
                name="ck_benefit_value_non_negative"
            ),
        ]
        indexes = [
            models.Index(fields=['segment', 'is_active'], name='idx_benefit_segment_active'),
            models.Index(fields=['active_from', 'active_to'], name='idx_benefit_date_range'),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.name} ({self.type})"
