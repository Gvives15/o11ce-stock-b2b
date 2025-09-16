"""Notification related services."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple

from django.utils import timezone
from django.db import transaction

from apps.notifications.models import Notification
from apps.stock.models import StockLot

_notifications: List[Dict[str, Any]] = []


def send_notification(user_id: int, message: str) -> Dict[str, Any]:
    """Pretend to send a notification to a user.

    The function stores the notification in a list and returns the created
    notification dictionary.
    """

    note = {"user_id": user_id, "message": message, "status": "sent"}
    _notifications.append(note)
    return note


class GenerateResult(NamedTuple):
    """Result of alert generation."""
    created: int
    skipped_rate_limited: int


def notify(event: str, payload: dict, channel: str = "system") -> Notification:
    """Create a notification/alert in the database."""
    return Notification.objects.create(
        event=event,
        channel=channel,
        payload=payload,
        created_at=timezone.now()
    )


def _should_skip_rate_limited(event: str, product_id: int = None, batch_id: int = None) -> bool:
    """Check if we should skip creating an alert due to rate limiting."""
    rate_limit_hours = int(os.getenv("ALERT_RATE_LIMIT_HOURS", "6"))
    cutoff = timezone.now() - timedelta(hours=rate_limit_hours)
    
    # Build filter for similar alerts in the time window
    filters = {
        "event": event,
        "created_at__gte": cutoff
    }
    
    if product_id:
        filters["payload__product_id"] = product_id
    if batch_id:
        filters["payload__batch_id"] = batch_id
    
    return Notification.objects.filter(**filters).exists()


def generate_low_stock_alerts() -> GenerateResult:
    """Generate alerts for products with low stock."""
    default_threshold = int(os.getenv("LOW_STOCK_THRESHOLD_DEFAULT", "5"))
    created = 0
    skipped = 0
    
    with transaction.atomic():
        # Get products with low stock
        low_stock_items = StockLot.objects.select_related("product").filter(
            qty_on_hand__lte=default_threshold,
            qty_on_hand__gt=0  # Don't alert on completely out of stock
        )
        
        for stock in low_stock_items:
            # Check rate limiting
            if _should_skip_rate_limited("low_stock", product_id=stock.product.id):
                skipped += 1
                continue
            
            # Create alert
            payload = {
                "product_id": stock.product.id,
                "product_name": stock.product.name,
                "current_stock": float(stock.qty_on_hand),
                "threshold": default_threshold,
                "lot_code": stock.lot_code,
                "warehouse": stock.warehouse.name if stock.warehouse else "Sin almacén"
            }
            
            notify(event="low_stock", payload=payload)
            created += 1
    
    return GenerateResult(created=created, skipped_rate_limited=skipped)


def generate_near_expiry_alerts() -> GenerateResult:
    """Generate alerts for products near expiry."""
    near_expiry_days = int(os.getenv("NEAR_EXPIRY_DAYS", "30"))
    cutoff_date = timezone.now().date() + timedelta(days=near_expiry_days)
    created = 0
    skipped = 0
    
    with transaction.atomic():
        # Get batches expiring soon
        expiring_items = StockLot.objects.select_related("product").filter(
            expiry_date__lte=cutoff_date,
            expiry_date__gte=timezone.now().date(),  # Not already expired
            qty_on_hand__gt=0
        )
        
        for stock in expiring_items:
            # Check rate limiting (by lot code, otherwise by product)
            lot_code = stock.lot_code
            if _should_skip_rate_limited("near_expiry", product_id=stock.product.id, batch_id=lot_code):
                skipped += 1
                continue
            
            # Calculate days until expiry
            days_until_expiry = (stock.expiry_date - timezone.now().date()).days
            
            # Create alert
            payload = {
                "product_id": stock.product.id,
                "product_name": stock.product.name,
                "lot_code": lot_code,
                "expiry_date": stock.expiry_date.isoformat(),
                "days_until_expiry": days_until_expiry,
                "quantity": float(stock.qty_on_hand),
                "warehouse": stock.warehouse.name if stock.warehouse else "Sin almacén"
            }
            
            notify(event="near_expiry", payload=payload)
            created += 1
    
    return GenerateResult(created=created, skipped_rate_limited=skipped)
