"""
Eventos del dominio POS.

Este módulo define todos los eventos que pueden ser publicados por el dominio POS,
siguiendo el patrón de eventos de dominio para desacoplar las operaciones POS
de otros dominios como Stock.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import List, Optional, Dict, Any
from uuid import UUID

from apps.events.base import DomainEvent


# ============================================================================
# EVENTOS DE VENTA
# ============================================================================

@dataclass
class SaleItemData:
    """Datos de un ítem de venta."""
    product_id: int
    product_name: str
    product_code: str
    sequence: int
    qty: Decimal
    unit_price: Decimal
    lot_id: Optional[int] = None
    lot_code: Optional[str] = None
    lot_override_reason: Optional[str] = None


@dataclass(frozen=True)
class SaleCreated(DomainEvent):
    """
    Evento publicado cuando se crea una nueva venta POS.
    
    Este evento se publica después de que la venta ha sido procesada exitosamente
    y todos los movimientos de stock han sido creados.
    """
    sale_id: str
    customer_id: Optional[int]
    user_id: int
    username: str
    items: List[SaleItemData]
    total_items: int
    total_amount: Decimal
    override_pin_used: bool
    
    def __post_init__(self):
        # Establecer aggregate_id antes de la validación base
        object.__setattr__(self, 'aggregate_id', self.sale_id)
        super().__post_init__()


@dataclass(frozen=True)
class SaleItemProcessed(DomainEvent):
    """
    Evento publicado cuando se procesa un ítem individual de una venta.
    
    Útil para sistemas que necesitan procesar ítem por ítem en lugar de
    la venta completa.
    """
    sale_id: str
    item_sequence: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    qty_sold: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    lot_id: Optional[int] = None
    lot_code: Optional[str] = None
    qty_from_lot: Optional[Decimal] = None
    movement_id: Optional[int] = None
    is_override: bool = False
    override_reason: Optional[str] = None
    # Compatibilidad con usos actuales
    item_data: Optional[SaleItemData] = None
    allocation_type: Optional[str] = None
    user_id: Optional[int] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', f"{self.sale_id}_{self.item_sequence if self.item_sequence is not None else 'unknown'}")
        super().__post_init__()


# ============================================================================
# EVENTOS DE OVERRIDE DE LOTES
# ============================================================================

@dataclass(frozen=True)
class LotOverrideRequested(DomainEvent):
    """
    Evento publicado cuando se solicita un override de lote.
    
    Se publica antes de procesar el override para permitir validaciones
    adicionales o auditoría preventiva.
    """
    sale_id: str
    user_id: int
    username: Optional[str] = None
    product_id: int
    product_name: Optional[str] = None
    lot_id: int
    lot_code: Optional[str] = None
    qty: Decimal
    reason: Optional[str] = None
    pin_provided: bool = False
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', f"{self.sale_id}_{self.product_id}_{self.lot_id}")
        super().__post_init__()


@dataclass(frozen=True)
class LotOverrideExecuted(DomainEvent):
    """
    Evento publicado cuando se ejecuta exitosamente un override de lote.
    
    Incluye información completa de la auditoría para sistemas de compliance.
    """
    sale_id: str
    user_id: int
    username: str
    product_id: int
    product_name: str
    lot_id: int
    lot_code: str
    qty_consumed: Decimal
    reason: str
    audit_id: Optional[int] = None
    movement_id: Optional[int] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', f"{self.sale_id}_{self.product_id}_{self.lot_id}")
        super().__post_init__()


# ============================================================================
# EVENTOS DE COTIZACIÓN
# ============================================================================

@dataclass
class PriceQuoteItemData:
    """Datos de un ítem en una cotización."""
    product_id: int
    product_name: str
    qty: Decimal
    unit: str
    unit_price: Decimal
    discount_item: Decimal
    subtotal: Decimal


@dataclass
class ComboDiscountData:
    """Datos de un descuento de combo aplicado."""
    name: str
    description: str
    discount_amount: Decimal
    items_affected: List[str]


@dataclass(frozen=True)
class PriceQuoteGenerated(DomainEvent):
    """
    Evento publicado cuando se genera una cotización de precios.
    
    Útil para análisis de pricing, seguimiento de cotizaciones y
    sistemas de CRM.
    """
    quote_id: str  # UUID generado para la cotización
    customer_id: int
    customer_name: str
    user_id: int
    username: str
    items: List[PriceQuoteItemData]
    combo_discounts: List[ComboDiscountData]
    subtotal: Decimal
    discounts_total: Decimal
    total: Decimal
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', self.quote_id)
        super().__post_init__()


# ============================================================================
# EVENTOS DE TRAZABILIDAD
# ============================================================================

@dataclass(frozen=True)
class SaleDetailRequested(DomainEvent):
    """
    Evento publicado cuando se solicita el detalle de una venta.
    
    Útil para auditoría de acceso a información sensible de trazabilidad.
    """
    sale_id: str
    requested_by_user_id: int
    requested_by_username: str
    access_granted: bool = False
    access_reason: str = "api_request"
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', f"{self.sale_id}_{self.requested_by_user_id}")
        super().__post_init__()


@dataclass(frozen=True)
class SaleDataExported(DomainEvent):
    """
    Evento publicado cuando se exportan datos de una venta.
    
    Importante para compliance y auditoría de exportación de datos.
    """
    sale_id: str
    export_format: str  # "csv", "json", etc.
    exported_by_user_id: int
    exported_by_username: str
    records_count: int
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', f"{self.sale_id}_{self.export_format}")
        super().__post_init__()


# ============================================================================
# EVENTOS DE VALIDACIÓN
# ============================================================================

@dataclass(frozen=True)
class StockValidationRequested(DomainEvent):
    """
    Evento publicado cuando POS necesita validar disponibilidad de stock.
    
    Permite que el dominio Stock responda con la información necesaria
    sin que POS tenga que importar directamente los servicios de Stock.
    """
    product_id: int
    qty: Decimal
    customer_id: Optional[int]
    min_shelf_life_days: int
    sale_id: Optional[str] = None
    validation_id: Optional[str] = None
    preferred_lot_id: Optional[int] = None
    allocation_type: Optional[str] = None
    user_id: Optional[int] = None
    qty_needed: Optional[Decimal] = None
    
    def __post_init__(self):
        agg_id = self.validation_id or self.sale_id or f"stock_validation_{self.product_id}"
        object.__setattr__(self, 'aggregate_id', agg_id)
        super().__post_init__()


@dataclass(frozen=True)
class CustomerValidationRequested(DomainEvent):
    """
    Evento publicado cuando POS necesita validar un cliente.
    
    Permite validar la existencia y obtener configuraciones del cliente
    sin imports directos.
    """
    validation_id: str
    customer_id: int
    sale_id: str
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', self.validation_id)
        super().__post_init__()


# ============================================================================
# EVENTOS DE ERROR
# ============================================================================

@dataclass(frozen=True)
class SaleProcessingFailed(DomainEvent):
    """
    Evento publicado cuando falla el procesamiento de una venta.
    
    Útil para sistemas de monitoreo y alertas.
    """
    sale_id: str
    user_id: int
    error_code: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    items_attempted: Optional[List[SaleItemData]] = None
    failure_stage: Optional[str] = None  # "validation", "allocation", "execution"
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', self.sale_id)
        super().__post_init__()


@dataclass(frozen=True)
class PriceQuoteProcessingFailed(DomainEvent):
    """
    Evento publicado cuando falla el procesamiento de una cotización.
    """
    quote_id: str
    customer_id: int
    user_id: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    items_attempted: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        object.__setattr__(self, 'aggregate_id', self.quote_id)
        super().__post_init__()