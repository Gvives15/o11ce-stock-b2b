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
    payload = models.JSONField()  # datos específicos del evento
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)  # null = pendiente

    class Meta:
        indexes = [
            models.Index(fields=['event', 'created_at'], name='idx_notification_event_date'),
            models.Index(fields=['channel', 'sent_at'], name='idx_notification_channel_sent'),
            models.Index(fields=['created_at'], name='idx_notification_created'),
            models.Index(fields=['sent_at'], name='idx_notification_sent'),
        ]

    def __str__(self) -> str:  # pragma: no cover
        status = "✓" if self.sent_at else "⏳"
        return f"{status} {self.event} → {self.channel}"
