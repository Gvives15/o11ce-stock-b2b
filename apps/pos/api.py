"""API endpoints for POS (Point of Sale) operations."""

from ninja import Router, Schema, Query
from ninja.errors import HttpError
from decimal import Decimal
from datetime import date
from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
import uuid

from apps.catalog.models import Product
from apps.catalog.utils import normalize_qty
from apps.catalog.pricing import price_quote
from apps.customers.models import Customer
from apps.panel.security import has_scope
from apps.pos.models import LotOverrideAudit
from apps.core.events import publish_pos_event
from .events import (
    SaleCreated,
    SaleItemProcessed,
    LotOverrideRequested,
    LotOverrideExecuted,
    PriceQuoteGenerated,
    SaleDetailRequested,
    SaleDataExported,
    StockValidationRequested,
    CustomerValidationRequested,
    SaleProcessingFailed,
    PriceQuoteProcessingFailed,
    SaleItemData
)

# Importar servicios en lugar de lógica directa
from .services import (
    handle_pos_sale_creation,
    handle_sale_detail_request,
    handle_price_quote_request
)

router = Router()


# ============================================================================
# SCHEMAS
# ============================================================================

class SaleItemIn(Schema):
    """Schema para un ítem de venta."""
    product_id: int
    qty: Decimal
    unit_price: Decimal
    sequence: int = 1  # Posición del ítem en la venta
    lot_id: Optional[int] = None
    lot_override_reason: Optional[str] = None


class SaleIn(Schema):
    """Schema para una venta POS."""
    items: List[SaleItemIn]
    customer_id: Optional[int] = None
    override_pin: Optional[str] = None


class SaleMovementOut(Schema):
    """Schema para movimiento de venta."""
    product_id: int
    product_name: str
    lot_id: int
    lot_code: str
    qty: Decimal
    unit_cost: Decimal


class SaleOut(Schema):
    """Schema para respuesta de venta."""
    sale_id: str
    total_items: int
    movements: List[SaleMovementOut]


# ============================================================================
# SCHEMAS PARA TRAZABILIDAD (BLOQUE G)
# ============================================================================

class ProductOut(Schema):
    """Schema para información básica de producto."""
    id: int
    code: str
    name: str


class LotDetailOut(Schema):
    """Schema para detalle de lote consumido."""
    lot_id: int
    lot_code: str
    expiry_date: Optional[date]
    qty: Decimal


class OverrideDetailOut(Schema):
    """Schema para información de override."""
    used: bool
    reason: Optional[str] = None
    actor: Optional[str] = None
    timestamp: Optional[date] = None


class SaleItemDetailOut(Schema):
    """Schema para detalle de ítem de venta con trazabilidad."""
    item_id: int
    product: ProductOut
    qty: Decimal
    unit_price: Decimal
    lots: List[LotDetailOut]
    override: OverrideDetailOut


class SaleDetailOut(Schema):
    """Schema para respuesta completa de detalle de venta."""
    sale_id: str
    items: List[SaleItemDetailOut]


# ============================================================================
# SCHEMAS PARA COTIZACIÓN DE PRECIOS
# ============================================================================

class PriceQuoteItemIn(Schema):
    """Schema para ítem en solicitud de cotización."""
    product_id: int
    qty: Decimal


class PriceQuoteIn(Schema):
    """Schema para solicitud de cotización de precios."""
    customer_id: int
    items: List[PriceQuoteItemIn]


class PriceQuoteItemOut(Schema):
    """Schema para ítem en respuesta de cotización."""
    product_id: int
    name: str
    qty: Decimal
    unit_price: Decimal
    discount_item: Decimal
    subtotal: Decimal


class PriceQuoteOut(Schema):
    """Schema para respuesta de cotización."""
    items: List[PriceQuoteItemOut]
    subtotal: Decimal
    segment_discount_amount: Decimal
    combo_discounts: List[dict]
    total_combo_discount: Decimal
    total: Decimal


class ErrorOut(Schema):
    """Schema para errores."""
    error: str
    detail: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health", response={200: dict})
def pos_health_check(request):
    """Health check para el router POS."""
    return {"status": "ok", "service": "pos"}


@router.post("/sale", response={200: SaleOut, 400: ErrorOut, 403: ErrorOut, 500: ErrorOut})
def create_pos_sale(request, sale_data: SaleIn):
    """
    Crea una venta POS con soporte para FEFO y override de lotes.
    
    Endpoint "tonto" que delega toda la lógica al servicio correspondiente.
    """
    # Convertir schema a dict para el servicio
    sale_dict = {
        'items': [
            {
                'product_id': item.product_id,
                'qty': item.qty,
                'unit_price': item.unit_price,
                'sequence': item.sequence,
                'lot_id': item.lot_id,
                'lot_override_reason': item.lot_override_reason
            }
            for item in sale_data.items
        ],
        'customer_id': sale_data.customer_id,
        'override_pin': sale_data.override_pin
    }
    
    # Delegar al servicio
    status_code, response_data = handle_pos_sale_creation(
        request_user=request.user,
        sale_data=sale_dict
    )
    
    # Convertir respuesta del servicio a schema si es exitosa
    if status_code == 200:
        movements_out = []
        for movement in response_data.get('movements', []):
            movements_out.append(SaleMovementOut(
                product_id=movement['product_id'],
                product_name=movement.get('product_name', 'Unknown'),
                lot_id=movement['lot_id'],
                lot_code=movement.get('lot_code', f"LOT-{movement['lot_id']}"),
                qty=movement['qty'],
                unit_cost=movement['unit_cost']
            ))
        
        return status_code, SaleOut(
            sale_id=response_data['sale_id'],
            total_items=response_data['total_items'],
            movements=movements_out
        )
    else:
        return status_code, ErrorOut(
            error=response_data['error'],
            detail=response_data['detail']
        )


@router.get("/sale/{sale_id}/detail", response={200: SaleDetailOut, 404: ErrorOut, 403: ErrorOut, 401: ErrorOut, 500: ErrorOut})
def get_sale_detail(request, sale_id: str):
    """
    Obtiene el detalle completo de una venta con trazabilidad de lotes.
    
    Endpoint "tonto" que delega toda la lógica al servicio correspondiente.
    """
    # Delegar al servicio
    status_code, response_data = handle_sale_detail_request(
        request_user=request.user,
        sale_id=sale_id
    )
    
    # Convertir respuesta del servicio a schema si es exitosa
    if status_code == 200:
        items_out = []
        for item in response_data.get('items', []):
            # Convertir lots
            lots_out = []
            for lot in item.get('lots', []):
                lots_out.append(LotDetailOut(
                    lot_id=lot['lot_id'],
                    lot_code=lot['lot_code'],
                    expiry_date=lot.get('expiry_date'),
                    qty=lot['qty_consumed']
                ))
            
            # Convertir override info
            override_info = item.get('override')
            override_out = OverrideDetailOut(
                used=bool(override_info),
                reason=override_info.get('reason') if override_info else None,
                actor=override_info.get('actor') if override_info else None,
                timestamp=override_info.get('timestamp') if override_info else None
            )
            
            items_out.append(SaleItemDetailOut(
                item_id=item['item_id'],
                product=ProductOut(
                    id=item['product']['id'],
                    code=item['product']['code'],
                    name=item['product']['name']
                ),
                qty=item['qty'],
                unit_price=item['unit_price'],
                lots=lots_out,
                override=override_out
            ))
        
        return status_code, SaleDetailOut(
            sale_id=sale_id,
            items=items_out
        )
    else:
        return status_code, ErrorOut(
            error=response_data['error'],
            detail=response_data['detail']
        )


@router.post("/price-quote", response={200: PriceQuoteOut, 400: ErrorOut, 404: ErrorOut, 500: ErrorOut})
def get_price_quote(request, data: PriceQuoteIn):
    """
    Endpoint para obtener cotización de precios con beneficios aplicados.
    
    Endpoint "tonto" que delega toda la lógica al servicio correspondiente.
    """
    # Convertir schema a dict para el servicio
    items_list = [
        {
            'product_id': item.product_id,
            'qty': item.qty
        }
        for item in data.items
    ]
    
    # Delegar al servicio
    status_code, response_data = handle_price_quote_request(
        customer_id=data.customer_id,
        items=items_list
    )
    
    # Convertir respuesta del servicio a schema si es exitosa
    if status_code == 200:
        items_out = []
        for item in response_data.get('items', []):
            items_out.append(PriceQuoteItemOut(
                product_id=item['product_id'],
                name=item['name'],
                qty=item['qty'],
                unit_price=item['unit_price'],
                discount_item=item['discount_item'],
                subtotal=item['subtotal']
            ))
        
        return status_code, PriceQuoteOut(
            items=items_out,
            subtotal=response_data['subtotal'],
            segment_discount_amount=response_data['segment_discount_amount'],
            combo_discounts=response_data['combo_discounts'],
            total_combo_discount=response_data['total_combo_discount'],
            total=response_data['total']
        )
    else:
        return status_code, ErrorOut(
            error=response_data['error'],
            detail=response_data['detail']
        )