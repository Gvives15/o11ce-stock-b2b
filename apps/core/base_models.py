from django.db import models


class TimeStampedModel(models.Model):
    """
    Modelo base abstracto que proporciona campos de timestamp automáticos.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True