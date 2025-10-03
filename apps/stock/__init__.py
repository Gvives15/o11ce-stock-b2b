"""
Stock Domain - Event-Driven Architecture

This module provides both legacy and event-driven APIs for stock management.
Version: 2.0.0 (Event-driven)
"""

# Lazy imports to avoid circular dependencies
def get_legacy_api():
    """Get legacy API functions."""
    from .services import (
        create_entry, create_exit, pick_lots_fefo,
        StockError, NotEnoughStock, NoLotsAvailable
    )
    return {
        'create_entry': create_entry,
        'create_exit': create_exit,
        'pick_lots_fefo': pick_lots_fefo,
        'StockError': StockError,
        'NotEnoughStock': NotEnoughStock,
        'NoLotsAvailable': NoLotsAvailable
    }

def get_event_driven_api():
    """Get event-driven API functions."""
    from .services import (
        request_stock_entry, request_stock_exit,
        validate_stock_availability, validate_warehouse
    )
    return {
        'request_stock_entry': request_stock_entry,
        'request_stock_exit': request_stock_exit,
        'validate_stock_availability': validate_stock_availability,
        'validate_warehouse': validate_warehouse
    }

def get_events():
    """Get stock events."""
    from . import events
    return events

def get_handlers():
    """Get stock event handlers."""
    from . import event_handlers
    return event_handlers

def get_models():
    """Get stock models."""
    from . import models
    return models

# Version info
__version__ = "2.0.0"
__api_version__ = "event-driven"