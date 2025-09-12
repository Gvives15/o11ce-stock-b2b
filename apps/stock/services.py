"""Utility services for stock management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

# In-memory store used purely for demonstration/testing purposes.
_inventory: List[Dict[str, Any]] = []


def record_entry(product_id: int, quantity: int, expires_at: datetime | None = None) -> Dict[str, Any]:
    """Register stock entry for a product.

    The implementation stores the information in a simple in-memory list so
    the service can be exercised without a database.  It returns the created
    entry dictionary.
    """

    if quantity <= 0:
        raise ValueError("quantity must be positive")

    entry = {
        "product_id": product_id,
        "quantity": quantity,
        "expires_at": expires_at,
    }
    _inventory.append(entry)
    return entry


def record_exit_fefo(product_id: int, quantity: int) -> List[Dict[str, Any]]:
    """Remove product using a *first-expire-first-out* strategy.

    Items with the earliest expiration date are removed first.  The function
    returns a list of dictionaries describing the removed stock batches.
    """

    if quantity <= 0:
        return []

    # Sort the inventory by expiration date (None means very far future)
    sorted_items = sorted(
        [i for i in _inventory if i["product_id"] == product_id],
        key=lambda i: i["expires_at"] or datetime.max,
    )

    removed: List[Dict[str, Any]] = []
    remaining = quantity

    for item in sorted_items:
        if remaining <= 0:
            break
        take = min(item["quantity"], remaining)
        removed.append(
            {
                "product_id": product_id,
                "quantity": take,
                "expires_at": item["expires_at"],
            }
        )
        item["quantity"] -= take
        remaining -= take

    # Clean up depleted inventory records
    _inventory[:] = [i for i in _inventory if i["quantity"] > 0]

    return removed
