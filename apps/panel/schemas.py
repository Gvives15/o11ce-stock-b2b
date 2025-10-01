"""Schemas para la API del panel administrativo"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from ninja import Schema


class UserScopeSchema(Schema):
    """Schema para scopes de usuario"""
    has_scope_users: bool
    has_scope_dashboard: bool
    has_scope_inventory: bool
    has_scope_inventory_level_1: bool
    has_scope_inventory_level_2: bool
    has_scope_orders: bool
    has_scope_customers: bool
    has_scope_reports: bool
    has_scope_analytics: bool
    has_scope_catalog: bool
    has_scope_caja: bool
    has_scope_pos_override: bool


class UserMeSchema(Schema):
    """Schema para información del usuario actual (/me endpoint)"""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: datetime
    last_login: Optional[datetime]
    scopes: UserScopeSchema
    roles: List[str]


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