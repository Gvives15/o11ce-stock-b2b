from django.db import models


class Customer(models.Model):
    class Segment(models.TextChoices):
        WHOLESALE = "wholesale", "Wholesale"
        RETAIL = "retail", "Retail"

    name = models.CharField(max_length=160, db_index=True)
    segment = models.CharField(max_length=16, choices=Segment.choices)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    tax_id = models.CharField(max_length=32, blank=True)  # CUIT/CUIL
    tax_condition = models.CharField(max_length=32, blank=True)  # IVA Responsable Inscripto, etc.
    min_shelf_life_days = models.IntegerField(
        default=0, 
        help_text="Días mínimos de vida útil requeridos para este cliente"
    )

    class Meta:
        indexes = [
            models.Index(fields=['segment'], name='idx_customer_segment'),
            models.Index(fields=['tax_id'], name='idx_customer_tax_id'),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.name
