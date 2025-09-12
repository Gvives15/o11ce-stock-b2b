from django.db import models


class Notification(models.Model):
    class Event(models.TextChoices):
        NEW_ORDER = "new_order", "New Order"
        LOW_STOCK = "low_stock", "Low Stock"
        NEAR_EXPIRY = "near_expiry", "Near Expiry"

    class Channel(models.TextChoices):
        PANEL = "panel", "Panel"
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"

    event = models.CharField(max_length=16, choices=Event.choices)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.event} via {self.channel}"
