"""Service functions for order operations."""

from __future__ import annotations

from typing import Any, Dict, List

from apps.stock.services import record_exit_fefo

_orders: List[Dict[str, Any]] = []


def checkout(order_id: int, items: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Process a checkout by consuming stock items.

    The function delegates stock removal to the stock service.  It returns a
    representation of the processed order.
    """

    if items is None:
        items = []

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 0)
        if product_id is not None and quantity:
            record_exit_fefo(product_id, quantity)

    order = {"order_id": order_id, "items": items, "status": "processed"}
    _orders.append(order)
    return order
