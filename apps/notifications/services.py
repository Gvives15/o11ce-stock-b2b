"""Notification related services."""

from __future__ import annotations

from typing import Any, Dict, List

_notifications: List[Dict[str, Any]] = []


def send_notification(user_id: int, message: str) -> Dict[str, Any]:
    """Pretend to send a notification to a user.

    The function stores the notification in a list and returns the created
    notification dictionary.
    """

    note = {"user_id": user_id, "message": message, "status": "sent"}
    _notifications.append(note)
    return note
