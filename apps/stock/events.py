"""
Domain events for Stock management.

This module defines all domain events related to stock operations,
including entries, exits, reservations, and inventory management.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import uuid4

from apps.events.base import DomainEvent


# ============================================================================
# STOCK ENTRY EVENTS
# ============================================================================

@dataclass(frozen=True)
class OrderStockValidationRequested(DomainEvent):
    """Solicitud de validación de stock para orden"""
    order_id: str = field(default="")
    customer_id: Optional[str] = field(default=None)
    warehouse_id: Optional[str] = field(default=None)
    items: List[Dict[str, Any]] = field(default_factory=list)
    validation_type: str = field(default="availability")  # "availability", "reservation"
    requested_by: Optional[str] = field(default=None)
    event_type: str = field(default="order.stock.validation.requested")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class OrderStockValidated(DomainEvent):
    """Validación de stock para orden completada"""
    order_id: str = field(default="")
    customer_id: Optional[str] = field(default=None)
    warehouse_id: Optional[str] = field(default=None)
    validation_status: str = field(default="valid")  # "valid", "invalid", "partial"
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    total_items: int = field(default=0)
    valid_items: int = field(default=0)
    invalid_items: int = field(default=0)
    validated_by: Optional[str] = field(default=None)
    validated_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="order.stock.validated")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class WarehouseValidated(DomainEvent):
    """Almacén validado"""
    warehouse_id: str = field(default="")
    warehouse_name: str = field(default="")
    validation_status: str = field(default="valid")  # "valid", "invalid"
    validation_errors: List[str] = field(default_factory=list)
    validated_by: Optional[str] = field(default=None)
    validated_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="warehouse.validated")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class LotExpired(DomainEvent):
    """Lote expirado"""
    lot_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    lot_code: str = field(default="")
    expiry_date: Optional[date] = field(default=None)
    quantity_expired: Decimal = field(default=Decimal('0'))
    event_type: str = field(default="lot.expired")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class LotQuarantined(DomainEvent):
    """Lote puesto en cuarentena"""
    lot_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    lot_code: str = field(default="")
    reason: str = field(default="")
    quarantined_by: Optional[str] = field(default=None)
    quarantined_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="lot.quarantined")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockReservationRequested(DomainEvent):
    """Solicitud de reserva de stock"""
    reservation_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    customer_id: Optional[str] = field(default=None)
    order_id: Optional[str] = field(default=None)
    expires_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="stock.reservation.requested")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockReserved(DomainEvent):
    """Stock reservado exitosamente"""
    reservation_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    reserved_lots: List[Dict[str, Any]] = field(default_factory=list)
    customer_id: Optional[str] = field(default=None)
    order_id: Optional[str] = field(default=None)
    expires_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="stock.reserved")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockReservationReleased(DomainEvent):
    """Reserva de stock liberada"""
    reservation_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    reason: str = field(default="")  # "expired", "cancelled", "fulfilled"
    released_lots: List[Dict[str, Any]] = field(default_factory=list)
    event_type: str = field(default="stock.reservation.released")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockUpdated(DomainEvent):
    """Stock actualizado"""
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    old_quantity: Decimal = field(default=Decimal('0'))
    new_quantity: Decimal = field(default=Decimal('0'))
    change_type: str = field(default="")  # "entry", "exit", "adjustment"
    reference_id: Optional[str] = field(default=None)
    event_type: str = field(default="stock.updated")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockThresholdUpdated(DomainEvent):
    """Umbral de stock actualizado"""
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    old_threshold: Decimal = field(default=Decimal('0'))
    new_threshold: Decimal = field(default=Decimal('0'))
    updated_by: Optional[str] = field(default=None)
    event_type: str = field(default="stock.threshold.updated")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockEntryRequested(DomainEvent):
    """Solicitud de entrada de stock"""
    # Todos los campos con valores por defecto para evitar problemas de herencia
    entry_id: str = field(default="")
    product_id: str = field(default="")
    lot_code: str = field(default="")
    expiry_date: Optional[date] = field(default=None)
    quantity: Decimal = field(default=Decimal('0'))
    unit_cost: Decimal = field(default=Decimal('0'))
    event_type: str = field(default="stock.entry.requested")
    event_version: str = field(default="1.0")
    warehouse_id: Optional[str] = field(default=None)
    reason: str = field(default="purchase")
    purchase_order_id: Optional[str] = field(default=None)
    supplier_id: Optional[str] = field(default=None)
    invoice_number: Optional[str] = field(default=None)
    received_by: Optional[str] = field(default=None)

    def __post_init__(self):
        super().__post_init__()
        if self.quantity and self.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        if self.unit_cost and self.unit_cost <= 0:
            raise ValueError("Unit cost must be greater than 0")


@dataclass(frozen=True)
class StockEntryValidated(DomainEvent):
    """Entrada de stock validada y lista para procesar"""
    # Todos los campos con valores por defecto
    entry_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    lot_code: str = field(default="")
    expiry_date: Optional[date] = field(default=None)
    quantity: Decimal = field(default=Decimal('0'))
    unit_cost: Decimal = field(default=Decimal('0'))
    reason: str = field(default="purchase")
    event_type: str = field(default="stock.entry.validated")
    event_version: str = field(default="1.0")
    warehouse_id: Optional[str] = field(default=None)
    warehouse_name: Optional[str] = field(default=None)
    product_exists: bool = field(default=True)
    product_active: bool = field(default=True)
    warehouse_exists: bool = field(default=True)
    warehouse_active: bool = field(default=True)


@dataclass(frozen=True)
class StockEntryProcessed(DomainEvent):
    """Entrada de stock procesada exitosamente"""
    entry_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: Optional[str] = field(default=None)
    lot_id: str = field(default="")
    lot_code: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    unit_cost: Decimal = field(default=Decimal('0'))
    total_cost: Decimal = field(default=Decimal('0'))
    processed_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="stock.entry.processed")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockEntryCompleted(DomainEvent):
    """Entrada de stock completada exitosamente"""
    entry_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    warehouse_id: Optional[str] = field(default=None)
    warehouse_name: Optional[str] = field(default=None)
    lot_id: str = field(default="")
    lot_code: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    unit_cost: Decimal = field(default=Decimal('0'))
    total_cost: Decimal = field(default=Decimal('0'))
    completed_at: Optional[datetime] = field(default=None)
    completed_by: Optional[str] = field(default=None)
    event_type: str = field(default="stock.entry.completed")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockEntryFailed(DomainEvent):
    """Entrada de stock falló"""
    entry_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: Optional[str] = field(default=None)
    reason: str = field(default="")
    error_message: str = field(default="")
    failed_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="stock.entry.failed")
    event_version: str = field(default="1.0")


# ============================================================================
# STOCK EXIT EVENTS
# ============================================================================

@dataclass(frozen=True)
class StockExitRequested(DomainEvent):
    """Solicitud de salida de stock"""
    exit_id: str = field(default="")
    product_id: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    reason: str = field(default="sale")
    event_type: str = field(default="stock.exit.requested")
    event_version: str = field(default="1.0")
    warehouse_id: Optional[str] = field(default=None)
    customer_id: Optional[str] = field(default=None)
    order_id: Optional[str] = field(default=None)
    requested_by: Optional[str] = field(default=None)


@dataclass(frozen=True)
class StockAllocationPlanned(DomainEvent):
    """Plan de asignación de stock para salida"""
    exit_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    warehouse_id: str = field(default="")
    warehouse_name: str = field(default="")
    requested_quantity: Decimal = field(default=Decimal('0'))
    allocated_lots: List[Dict[str, Any]] = field(default_factory=list)
    total_allocated: Decimal = field(default=Decimal('0'))
    is_fully_allocated: bool = field(default=True)
    event_type: str = field(default="stock.allocation.planned")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockExitCompleted(DomainEvent):
    """Salida de stock completada exitosamente"""
    exit_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    warehouse_id: str = field(default="")
    warehouse_name: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    allocated_lots: List[Dict[str, Any]] = field(default_factory=list)
    completed_at: Optional[datetime] = field(default=None)
    completed_by: Optional[str] = field(default=None)
    event_type: str = field(default="stock.exit.completed")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockExitFailed(DomainEvent):
    """Salida de stock falló"""
    exit_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: Optional[str] = field(default=None)
    reason: str = field(default="")
    error_message: str = field(default="")
    failed_at: Optional[datetime] = field(default=None)
    event_type: str = field(default="stock.exit.failed")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockExitValidated(DomainEvent):
    """Salida de stock validada"""
    exit_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    quantity: Decimal = field(default=Decimal('0'))
    reason: str = field(default="sale")
    allocated_lots: List[Dict[str, Any]] = field(default_factory=list)
    event_type: str = field(default="stock.exit.validated")
    event_version: str = field(default="1.0")
    warehouse_id: Optional[str] = field(default=None)
    warehouse_name: Optional[str] = field(default=None)
    product_exists: bool = field(default=True)
    product_active: bool = field(default=True)
    warehouse_exists: bool = field(default=True)
    warehouse_active: bool = field(default=True)
    sufficient_stock: bool = field(default=True)


@dataclass(frozen=True)
class StockExitProcessed(DomainEvent):
    """Evento emitido cuando una salida de stock ha sido procesada exitosamente"""
    exit_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    lot_code: str = field(default="")
    quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    unit_cost: Decimal = field(default_factory=lambda: Decimal('0'))
    reason: str = field(default="")
    warehouse_id: str = field(default="")
    warehouse_name: str = field(default="")
    processed_at: datetime = field(default_factory=datetime.now)
    processed_by: str = field(default="")
    
    event_type: str = field(default="stock.exit.processed")
    event_version: str = field(default="1.0")


# ============================================================================
# VALIDATION EVENTS
# ============================================================================

@dataclass(frozen=True)
class ProductValidationRequested(DomainEvent):
    """Solicitud de validación de producto"""
    validation_id: str = field(default="")
    product_id: str = field(default="")
    requested_by_domain: str = field(default="")
    event_type: str = field(default="product.validation.requested")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class ProductValidated(DomainEvent):
    """Producto validado"""
    validation_id: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    product_exists: bool = field(default=True)
    product_active: bool = field(default=True)
    allows_stock_management: bool = field(default=True)
    unit_of_measure: str = field(default="")
    requires_lot_tracking: bool = field(default=False)
    requires_expiry_tracking: bool = field(default=False)
    minimum_stock_level: Decimal = field(default=Decimal('0'))
    event_type: str = field(default="product.validated")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockValidated(DomainEvent):
    """Stock validado"""
    validation_id: str = field(default="")
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    requested_quantity: Decimal = field(default=Decimal('0'))
    available_quantity: Decimal = field(default=Decimal('0'))
    is_sufficient: bool = field(default=True)
    allocated_lots: List[Dict[str, Any]] = field(default_factory=list)
    event_type: str = field(default="stock.validated")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockValidationRequested(DomainEvent):
    """Evento emitido cuando se solicita validación de stock"""
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    operation_type: str = field(default="")  # 'entry' or 'exit'
    
    event_type: str = field(default="stock.validation.requested")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class WarehouseValidationRequested(DomainEvent):
    """Evento emitido cuando se solicita validación de almacén"""
    warehouse_id: str = field(default="")
    operation_type: str = field(default="")
    
    event_type: str = field(default="warehouse.validation.requested")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class LotExpiryWarning(DomainEvent):
    """Evento emitido cuando un lote está próximo a vencer"""
    lot_code: str = field(default="")
    product_id: str = field(default="")
    product_name: str = field(default="")
    expiry_date: date = field(default_factory=date.today)
    days_until_expiry: int = field(default=0)
    quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    warehouse_id: str = field(default="")
    
    event_type: str = field(default="stock.lot.expiry.warning")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class LowStockDetected(DomainEvent):
    """Evento emitido cuando se detecta stock bajo"""
    product_id: str = field(default="")
    product_name: str = field(default="")
    product_sku: str = field(default="")
    current_quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    minimum_quantity: Decimal = field(default_factory=lambda: Decimal('0'))
    warehouse_id: str = field(default="")
    warehouse_name: str = field(default="")
    
    event_type: str = field(default="stock.low.detected")
    event_version: str = field(default="1.0")


@dataclass(frozen=True)
class StockNotificationRequested(DomainEvent):
    """Evento emitido cuando se solicita una notificación de stock"""
    notification_type: str = field(default="")  # 'low_stock', 'expiry_warning', etc.
    product_id: str = field(default="")
    warehouse_id: str = field(default="")
    message: str = field(default="")
    priority: str = field(default="normal")  # 'low', 'normal', 'high', 'critical'
    
    event_type: str = field(default="stock.notification.requested")
    event_version: str = field(default="1.0")