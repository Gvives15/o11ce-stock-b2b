"""Schemas para la API del panel administrativo"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from ninja import Schema


class OrderItemSchema(Schema):
    """Schema para items de orden"""
    id: int
    product_code: str
    product_name: str
    qty: int
    unit_price: Decimal
    total_price: Decimal


class OrderListSchema(Schema):
    """Schema para listado de órdenes"""
    id: int
    customer: Dict[str, Any]
    status: str
    total: Decimal
    delivery_method: str
    requested_delivery_date: Optional[datetime]
    created_at: datetime
    items_count: int


class OrderListResponse(Schema):
    """Schema para respuesta de listado de órdenes"""
    items: List[OrderListSchema]
    next_cursor: Optional[str] = None
    has_next: bool = False


class OrderDetailSchema(Schema):
    """Schema para detalle de orden"""
    id: int
    customer: Dict[str, Any]
    status: str
    currency: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    delivery_method: str
    delivery_address_text: str
    delivery_window_from: Optional[str]
    delivery_window_to: Optional[str]
    delivery_instructions: str
    requested_delivery_date: Optional[str]
    created_at: datetime
    items: List[OrderItemSchema]
    valid_next_states: List[str]


class StatusChangeRequest(Schema):
    """Schema para solicitud de cambio de estado"""
    status: str
    reason: Optional[str] = None


class StatusChangeResponse(Schema):
    """Schema para respuesta de cambio de estado"""
    id: int
    old_status: str
    new_status: str
    changed_at: str
    changed_by: str