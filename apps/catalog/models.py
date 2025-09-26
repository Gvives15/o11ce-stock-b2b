from django.db import models
from django.db.models import Q
from apps.core.base_models import TimeStampedModel

try:
    from django.contrib.postgres.indexes import GinIndex
    from django.contrib.postgres.search import TrigramSimilarity
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class Product(TimeStampedModel):
    class Unit(models.TextChoices):
        UNIT = "unit", "Unidad"
        PACKAGE = "package", "Paquete"
        # Legacy choices for backward compatibility
        KILOGRAM = "KG", "Kilogramo"
        LITER = "LT", "Litro"

    class Segment(models.TextChoices):
        WHOLESALE = "wholesale", "Wholesale"
        RETAIL = "retail", "Retail"

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=160, db_index=True)
    brand = models.CharField(max_length=80, blank=True)
    unit = models.CharField(max_length=8, choices=Unit.choices, default=Unit.UNIT)
    category = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=21)  # %
    segment = models.CharField(max_length=16, choices=Segment.choices, null=True, blank=True, help_text="Segmento de mercado objetivo (opcional)")
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    pack_size = models.IntegerField(null=True, blank=True, help_text="Número de unidades por paquete")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(price__gt=0), 
                name="ck_product_price_positive"
            ),
            models.CheckConstraint(
                check=Q(tax_rate__gte=0) & Q(tax_rate__lte=100), 
                name="ck_product_tax_rate_valid"
            ),
            models.CheckConstraint(
                check=Q(pack_size__isnull=True) | Q(pack_size__gt=0),
                name="ck_product_pack_size_positive"
            ),
        ]
        indexes = [
            models.Index(fields=['is_active', 'category'], name='idx_product_active_category'),
            models.Index(fields=['brand'], name='idx_product_brand'),
        ]
        
        # Agregar índices GIN para PostgreSQL si está disponible
        if POSTGRES_AVAILABLE:
            try:
                indexes.extend([
                    GinIndex(fields=['name'], name='gin_product_name_trgm', opclasses=['gin_trgm_ops']),
                    GinIndex(fields=['code'], name='gin_product_code_trgm', opclasses=['gin_trgm_ops']),
                ])
            except:
                pass  # Fallback si no se puede crear el índice

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.code} · {self.name}"


class Benefit(TimeStampedModel):
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
            # Validación condicional: si type='discount' => value obligatorio y 0..100
            models.CheckConstraint(
                check=(
                    Q(type='discount', value__isnull=False, value__gte=0, value__lte=100) |
                    Q(type='combo')
                ),
                name="ck_benefit_discount_value_required"
            ),
            # Validación condicional: si type='combo' => combo_spec obligatorio
            models.CheckConstraint(
                check=(
                    Q(type='combo', combo_spec__isnull=False) |
                    Q(type='discount')
                ),
                name="ck_benefit_combo_spec_required"
            ),
        ]
        indexes = [
            models.Index(fields=['segment', 'is_active'], name='idx_benefit_segment_active'),
            models.Index(fields=['active_from', 'active_to'], name='idx_benefit_date_range'),
            models.Index(fields=['type'], name='idx_benefit_type'),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.name} ({self.type})"
