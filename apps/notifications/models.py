from django.db import models


class Notification(models.Model):
    """Simple notification model for customers."""

    customer = models.ForeignKey(
        "customers.Customer",
        related_name="notifications",
        on_delete=models.CASCADE,
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Notification to {self.customer}"

