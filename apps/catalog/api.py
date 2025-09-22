
"""API endpoints for the catalog application."""

from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from ninja import Router, Schema
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.catalog.models import Product, Benefit
from apps.catalog.utils import get_active_benefits
from apps.core.cache_service import CacheService, cache_response
import logging

logger = logging.getLogger(__name__)

router = Router()

# Schemas
class ProductIn(Schema):
    code: str
    name: str
    price: Decimal
    tax_rate: Decimal = 21
    unit: str = "UN"
    brand: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True

class ProductOut(Schema):
    id: int
    code: str
    name: str
    price: Decimal
    tax_rate: Decimal
    unit: str
    brand: Optional[str] = None
    category: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class BenefitOut(Schema):
    id: int
    name: str
    type: str
    segment: str
    value: Optional[Decimal] = None
    combo_spec: Optional[dict] = None
    active_from: datetime
    active_to: datetime
    is_active: bool

class ErrorOut(Schema):
    error: str
    message: str

# Endpoints
@router.post("/products", response={201: ProductOut, 409: ErrorOut, 400: ErrorOut})
def create_product(request, payload: ProductIn):
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    logger.info(f"Creating product - Request ID: {request_id}, Code: {payload.code}")
    
    try:
        p = Product.objects.create(**payload.dict())
        # Invalidar cache de productos al crear
        CacheService.invalidate_pattern("catalog_products")
        return 201, ProductOut.from_orm(p)
    except IntegrityError:
        return 409, {"error": "CONFLICT", "message": "code ya existe"}
    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}

@router.get("/products", response=List[ProductOut])
@cache_response(timeout=90, key_prefix="catalog_products")
def list_products(request, 
                 search: Optional[str] = None, 
                 brand: Optional[str] = None,
                 category: Optional[str] = None,
                 is_active: Optional[bool] = None,
                 page: int = 1, 
                 page_size: int = 20):
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    
    # Log de acceso con métricas
    logger.info(f"API_ACCESS /products - Request ID: {request_id}, Search: {search}, Brand: {brand}, Category: {category}, Page: {page}")
    logger.info(f"METRIC products_endpoint_hit 1 request_id={request_id}")
    
    qs = Product.objects.all()
    
    # Filtros
    if search:
        qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search) | Q(brand__icontains=search))
    if brand:
        qs = qs.filter(brand__icontains=brand)
    if category:
        qs = qs.filter(category__icontains=category)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    
    qs = qs.order_by("name")[(page - 1) * page_size : page * page_size]
    results = [ProductOut.from_orm(p) for p in qs]
    
    # Log de respuesta con métricas
    logger.info(f"API_RESPONSE /products - Request ID: {request_id}, Results: {len(results)}")
    
    return results

@router.get("/offers", response=List[BenefitOut])
@cache_response(timeout=60, key_prefix="catalog_offers")
def list_offers(request,
               segment: Optional[str] = None,
               date_filter: Optional[str] = None):
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    
    # Log de acceso con métricas
    logger.info(f"API_ACCESS /offers - Request ID: {request_id}, Segment: {segment}, Date: {date_filter}")
    logger.info(f"METRIC offers_endpoint_hit 1 request_id={request_id}")
    
    # Usar fecha actual si no se especifica
    filter_date = timezone.now().date()
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    # Usar helper para obtener beneficios activos
    benefits = get_active_benefits(segment, filter_date)
    results = [BenefitOut.from_orm(b) for b in benefits]
    
    # Log de respuesta con métricas
    logger.info(f"API_RESPONSE /offers - Request ID: {request_id}, Results: {len(results)}")
    
    return results

@router.get("/products/{product_id}", response={200: ProductOut, 404: ErrorOut})
def get_product(request, product_id: int):
    try:
        p = Product.objects.get(id=product_id)
        return ProductOut.from_orm(p)
    except Product.DoesNotExist:
        return 404, {"error": "NOT_FOUND", "message": "producto no encontrado"}

@router.patch("/products/{product_id}", response={200: ProductOut, 404: ErrorOut})
def update_product(request, product_id: int, payload: ProductIn):
    try:
        p = Product.objects.get(id=product_id)
        for k, v in payload.dict().items():
            setattr(p, k, v)
        p.save()
        # Invalidar cache de productos al actualizar
        CacheService.invalidate_pattern("catalog_products")
        return ProductOut.from_orm(p)
    except Product.DoesNotExist:
        return 404, {"error": "NOT_FOUND", "message": "producto no encontrado"}

@router.get("/ping")
def ping(request) -> dict:
    """Simple endpoint used for smoke testing the catalog API."""
    return {"message": "catalog pong"}

