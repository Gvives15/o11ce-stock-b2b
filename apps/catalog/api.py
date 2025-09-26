
"""API endpoints for the catalog application."""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from ninja import Router, Schema
from ninja.errors import HttpError
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.catalog.models import Product, Benefit
from apps.catalog.utils import get_active_benefits, calculate_final_price
from apps.catalog.pricing import price_quote
from apps.customers.models import Customer
from apps.stock.services import allocate_lots_fefo, StockError
from apps.core.cache_service import CacheService, cache_response
from apps.core.permissions import vendedor_required
import logging
import re

logger = logging.getLogger(__name__)

router = Router()


def extract_pack_size(product_name: str) -> Optional[str]:
    """
    Extract pack size from product name.
    
    Examples:
    - "Galletas Caja x10 unidades" -> "10"
    - "Galletitas Dulces Pack x6" -> "6"
    - "Gaseosa 500ml" -> None
    """
    # Pattern to match "x" followed by digits
    pattern = r'x(\d+)'
    match = re.search(pattern, product_name, re.IGNORECASE)
    
    if match:
        return match.group(1)
    
    return None

# Schemas
class ProductIn(Schema):
    code: str
    name: str
    price: Decimal
    tax_rate: Decimal = 21
    unit: str = "UN"
    brand: Optional[str] = None
    category: Optional[str] = None

class ProductFilters(Schema):
    search: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    segment: Optional[str] = None  # Agregar segment para calcular final_price
    page: int = 1
    page_size: int = 20
    is_active: bool = True

class ProductOut(Schema):
    id: int
    code: str
    name: str
    price: Decimal
    final_price: Decimal  # Nuevo campo
    tax_rate: Decimal
    unit: str
    brand: Optional[str] = None
    category: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @staticmethod
    def from_product(product: Product, segment: Optional[str] = None) -> 'ProductOut':
        """Crear ProductOut con final_price calculado."""
        final_price = calculate_final_price(product, segment)
        
        return ProductOut(
            id=product.id,
            code=product.code,
            name=product.name,
            price=product.price,
            final_price=final_price,
            tax_rate=product.tax_rate,
            unit=product.unit,
            brand=product.brand,
            category=product.category,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at
        )

class BenefitOut(Schema):
    id: int
    name: str
    type: str
    segment: str
    value: Optional[Decimal] = None
    combo_spec: Optional[dict] = None
    active_from: date
    active_to: date
    is_active: bool

class ErrorOut(Schema):
    error: str
    message: str

# Search specific schemas
class ProductSearchResult(Schema):
    id: int
    sku: str  # This will be the 'code' field
    name: str
    unit: str
    pack_size: Optional[str] = None  # For future pack size support
    price_base: Decimal
    final_price: Decimal  # Agregar final_price también al search
    
    @staticmethod
    def from_product(product: Product, segment: Optional[str] = None) -> 'ProductSearchResult':
        """Crear ProductSearchResult con final_price calculado."""
        final_price = calculate_final_price(product, segment)
        pack_size = extract_pack_size(product.name)
        
        return ProductSearchResult(
            id=product.id,
            sku=product.code,
            name=product.name,
            unit=product.unit,
            pack_size=pack_size,
            price_base=product.price,
            final_price=final_price
        )

class SearchResponse(Schema):
    results: List[ProductSearchResult]
    next: Optional[str] = None

# Pricing endpoint schemas
class PricingItemIn(Schema):
    product_id: int
    quantity: Decimal

class PricingRequest(Schema):
    customer_id: int
    items: List[PricingItemIn]

class PricingItemOut(Schema):
    product_id: int
    name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal

class PricingResponse(Schema):
    items: List[PricingItemOut]
    subtotal: Decimal
    segment_discount_amount: Decimal
    combo_discounts: List[dict]
    total_combo_discount: Decimal
    total: Decimal
    stock_validated: bool = True

# Endpoints
@router.post("/products", response={201: ProductOut, 409: ErrorOut, 400: ErrorOut})
def create_product(request, payload: ProductIn):
    from apps.catalog.cache_segment import segment_cache
    
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    logger.info(f"Creating product - Request ID: {request_id}, Code: {payload.code}")
    
    try:
        p = Product.objects.create(**payload.dict())
        
        # Invalidar cache de productos al crear (tanto general como por segmento)
        CacheService.invalidate_pattern("catalog_products")
        segment_cache.invalidate_segment("retail")
        segment_cache.invalidate_segment("wholesale")
        
        return 201, ProductOut.from_orm(p)
    except IntegrityError:
        return 409, {"error": "CONFLICT", "message": "code ya existe"}
    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}

@router.get("/products", response=List[ProductOut])
def list_products(request, 
                 search: Optional[str] = None, 
                 brand: Optional[str] = None,
                 category: Optional[str] = None,
                 is_active: Optional[bool] = None,
                 segment: Optional[str] = None,
                 page: int = 1, 
                 page_size: int = 20):
    from apps.catalog.cache_segment import segment_cache
    
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    
    # Manually extract parameters from request.GET if not provided
    if search is None and 'search' in request.GET:
        search = request.GET.get('search')
    if segment is None and 'segment' in request.GET:
        segment = request.GET.get('segment')
    
    # Prepare filters for cache key generation
    filters = {
        'search': search,
        'brand': brand,
        'category': category,
        'is_active': is_active,
        'page': page,
        'page_size': page_size
    }
    # Remove None values for cleaner cache keys
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # Try to get from segment-differentiated cache first
    cached_results = segment_cache.get_products_list(segment, filters)
    if cached_results is not None:
        logger.info(f"API_CACHE_HIT /products - Request ID: {request_id}, Segment: {segment}")
        return cached_results
    
    # Cache miss - execute query
    logger.info(f"API_ACCESS /products - Request ID: {request_id}, Search: {search}, Brand: {brand}, Category: {category}, Segment: {segment}, Page: {page}")
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
    results = [ProductOut.from_product(p, segment) for p in qs]
    
    # Cache the results with segment differentiation
    # Use shorter timeout for dynamic pricing data
    cache_timeout = 180 if segment else 300  # 3 min for segment-specific, 5 min for generic
    segment_cache.set_products_list(results, segment, filters, cache_timeout)
    
    # Log de respuesta con métricas
    logger.info(f"API_RESPONSE /products - Request ID: {request_id}, Results: {len(results)}, Cached: True")
    
    return results

@router.get("/offers", response=List[BenefitOut])
def list_offers(request, segment: Optional[str] = None, date_filter: Optional[str] = None):
    from apps.catalog.cache_segment import segment_cache
    
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    
    # Manually extract segment parameter from request.GET if not provided
    if segment is None and 'segment' in request.GET:
        segment = request.GET.get('segment')
    if date_filter is None and 'date_filter' in request.GET:
        date_filter = request.GET.get('date_filter')
    
    # Prepare cache parameters
    cache_params = {'date_filter': date_filter} if date_filter else None
    
    # Try to get from segment-differentiated cache first
    cached_benefits = segment_cache.get_active_benefits(segment)
    if cached_benefits is not None and not date_filter:  # Only use cache if no date filter
        logger.info(f"API_CACHE_HIT /offers - Request ID: {request_id}, Segment: {segment}")
        return cached_benefits
    
    # Cache miss or date filter present - execute query
    logger.info(f"API_ACCESS /offers - Request ID: {request_id}, Segment: {segment}, Date: {date_filter}")
    logger.info(f"METRIC offers_endpoint_hit 1 request_id={request_id}")
    
    # Parse date filter if provided
    filter_date = None
    if date_filter:
        try:
            filter_date = datetime.fromisoformat(date_filter).date()
        except ValueError:
            filter_date = timezone.now().date()
    
    # Usar helper para obtener beneficios activos
    benefits = get_active_benefits(segment, filter_date)
    results = [BenefitOut.from_orm(b) for b in benefits]
    
    # Cache the results if no date filter (for current date benefits)
    if not date_filter:
        # Use shorter timeout for benefits as they can change more frequently
        cache_timeout = 120  # 2 minutes for benefits
        segment_cache.set_active_benefits(results, segment, cache_timeout)
    
    # Log de respuesta con métricas
    logger.info(f"API_RESPONSE /offers - Request ID: {request_id}, Results: {len(results)}, Cached: {not date_filter}")
    
    return results

@router.get("/products/{product_id}", response={200: ProductOut, 404: ErrorOut})
def get_product(request, product_id: int, segment: Optional[str] = None):
    try:
        p = Product.objects.get(id=product_id)
        return ProductOut.from_product(p, segment)
    except Product.DoesNotExist:
        return 404, {"error": "NOT_FOUND", "message": "producto no encontrado"}

@router.patch("/products/{product_id}", response={200: ProductOut, 404: ErrorOut})
def update_product(request, product_id: int, payload: ProductIn, segment: Optional[str] = None):
    from apps.catalog.cache_segment import segment_cache
    
    try:
        p = Product.objects.get(id=product_id)
        for k, v in payload.dict().items():
            setattr(p, k, v)
        p.save()
        
        # Invalidar cache de productos al actualizar (tanto general como por segmento)
        CacheService.invalidate_pattern("catalog_products")
        segment_cache.invalidate_product(product_id)
        
        return ProductOut.from_product(p, segment)
    except Product.DoesNotExist:
        return 404, {"error": "NOT_FOUND", "message": "producto no encontrado"}

@router.get("/search", response=SearchResponse)
def search_products(request, 
                   q: Optional[str] = None, 
                   segment: Optional[str] = None,
                   page: int = 1, 
                   size: int = 20):
    """
    Search products by name or SKU with pagination.
    
    Args:
        q: Search query (searches in name and code/sku fields)
        segment: Customer segment for price calculation (retail/wholesale)
        page: Page number (1-based)
        size: Number of items per page
        
    Returns:
        SearchResponse with results and next page URL
    """
    request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', 'unknown')
    
    # Manually extract segment parameter from request.GET if not provided
    if segment is None and 'segment' in request.GET:
        segment = request.GET.get('segment')
    
    # Log de acceso con métricas
    logger.info(f"API_ACCESS /search - Request ID: {request_id}, Query: {q}, Segment: {segment}, Page: {page}, Size: {size}")
    logger.info(f"METRIC search_endpoint_hit 1 request_id={request_id}")
    
    # Base queryset - only active products
    qs = Product.objects.filter(is_active=True)
    
    # Apply search filter if query provided
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
    
    # Order by name for consistent pagination
    qs = qs.order_by('name')
    
    # Calculate pagination
    total_count = qs.count()
    start_index = (page - 1) * size
    end_index = start_index + size
    
    # Get results for current page
    products = qs[start_index:end_index]
    
    # Build results using the new schema with final_price
    results = [ProductSearchResult.from_product(product, segment) for product in products]
    
    # Calculate next page URL
    next_url = None
    if end_index < total_count:
        next_url = f"/api/v1/catalog/search?q={q or ''}&segment={segment or ''}&page={page + 1}&size={size}"
    
    # Log de respuesta con métricas
    logger.info(f"API_RESPONSE /search - Request ID: {request_id}, Results: {len(results)}, Total: {total_count}")
    
    return SearchResponse(
        results=results,
        next=next_url
    )

@router.get("/ping")
def ping(request) -> dict:
    """Simple endpoint used for smoke testing the catalog API."""
    return {"message": "catalog pong"}

def validate_stock_availability(items_data: List[dict]) -> None:
    """
    Valida disponibilidad de stock para una lista de items usando FEFO.
    
    Args:
        items_data: Lista de diccionarios con 'product_id' y 'quantity'
        
    Raises:
        HttpError: 409 si no hay stock suficiente para algún producto
    """
    for item_data in items_data:
        try:
            product = Product.objects.get(id=item_data['product_id'])
            quantity = item_data['quantity']
            
            # Usar allocate_lots_fefo para validar stock sin realizar la asignación
            # Solo validamos que hay stock suficiente
            allocate_lots_fefo(
                product=product,
                qty_needed=quantity,
                chosen_lot_id=None,
                min_shelf_life_days=0,
                warehouse_id=None
            )
            
        except Product.DoesNotExist:
            # Si el producto no existe, lo ignoramos (igual que price_quote)
            continue
        except StockError as e:
            if e.code == "INSUFFICIENT_STOCK":
                raise HttpError(
                    409, 
                    f"Stock insuficiente para producto {product.name} (ID: {product.id}). "
                    f"Solicitado: {quantity}. {str(e)}"
                )
            else:
                # Otros errores de stock se tratan como errores internos
                logger.error(f"Error interno en /catalog/pricing: {str(e)}")
                raise HttpError(500, f"Error de validación de stock: {str(e)}")


@router.post("/pricing", response={200: PricingResponse, 400: ErrorOut, 409: ErrorOut, 422: ErrorOut, 500: ErrorOut})
def calculate_pricing_with_stock_validation(request, payload: PricingRequest):
    """
    Calcula precios con descuentos aplicados y valida disponibilidad de stock.
    
    Este endpoint combina el cálculo de precios del motor de pricing existente
    con validación de stock usando FEFO. Retorna error 409 si no hay stock suficiente.
    
    Args:
        payload: Datos de la solicitud con customer_id e items
        
    Returns:
        PricingResponse: Precios calculados con validación de stock confirmada
        
    Raises:
        400: Datos de entrada inválidos
        401: No autorizado (manejado por middleware)
        409: Stock insuficiente para uno o más productos
        422: Error de validación
        500: Error interno del servidor
    """
    try:
        # Validaciones básicas
        if not payload.items:
            raise HttpError(400, "Debe incluir al menos un item")
        
        if len(payload.items) > 50:
            raise HttpError(400, "Máximo 50 items permitidos por solicitud")
        
        # Validar cantidades positivas
        for item in payload.items:
            if item.quantity <= 0:
                raise HttpError(400, f"La cantidad debe ser mayor a 0 para el producto {item.product_id}")
        
        # Obtener cliente
        try:
            customer = Customer.objects.get(id=payload.customer_id)
        except Customer.DoesNotExist:
            raise HttpError(404, "Cliente no encontrado")
        
        # Preparar items para validación y pricing
        items_data = []
        for item in payload.items:
            items_data.append({
                'product_id': item.product_id,
                'quantity': item.quantity
            })
        
        # VALIDAR STOCK PRIMERO - esto puede lanzar HttpError 409
        validate_stock_availability(items_data)
        
        # Si llegamos aquí, el stock está disponible, proceder con pricing
        quote = price_quote(customer, items_data)
        
        # Convertir el resultado a nuestro schema de respuesta
        response_items = []
        for pricing_item in quote.items:
            response_items.append(PricingItemOut(
                product_id=pricing_item.product.id,
                name=pricing_item.product.name,
                quantity=pricing_item.quantity,
                unit_price=pricing_item.unit_price,
                subtotal=pricing_item.subtotal
            ))
        
        return PricingResponse(
            items=response_items,
            subtotal=quote.subtotal,
            segment_discount_amount=quote.segment_discount_amount,
            combo_discounts=[combo.__dict__ for combo in quote.combo_discounts],
            total_combo_discount=quote.total_combo_discount,
            total=quote.total,
            stock_validated=True
        )
        
    except HttpError:
        # Re-raise HttpErrors (400, 401, 409, etc.)
        raise
    except Exception as e:
        # Cualquier otro error se trata como error interno
        logger.error(f"Error interno en /catalog/pricing: {str(e)}")
        raise HttpError(500, "Error interno del servidor")