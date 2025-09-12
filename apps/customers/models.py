from django.db import models


class Customer(models.Model):
    class Segment(models.TextChoices):
        WHOLESALE = "wholesale", "Wholesale"
        RETAIL = "retail", "Retail"

    name = models.CharField(max_length=160, db_index=True)
    segment = models.CharField(max_length=16, choices=Segment.choices)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    tax_id = models.CharField(max_length=32, blank=True)
    tax_condition = models.CharField(max_length=32, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name
