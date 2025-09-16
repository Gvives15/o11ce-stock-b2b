
"""API endpoints for the catalog application."""

from decimal import Decimal
from typing import Optional, List
from ninja import Router, Schema
from django.db import IntegrityError
from django.db.models import Q
from .models import Product

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
    is_active: bool

class ErrorOut(Schema):
    error: str
    message: str

# Endpoints
@router.post("/products", response={201: ProductOut, 409: ErrorOut, 400: ErrorOut})
def create_product(request, payload: ProductIn):
    try:
        p = Product.objects.create(**payload.dict())
        return 201, ProductOut.from_orm(p)
    except IntegrityError:
        return 409, {"error": "CONFLICT", "message": "code ya existe"}
    except Exception as e:
        return 400, {"error": "VALIDATION_ERROR", "message": str(e)}

@router.get("/products", response=List[ProductOut])
def list_products(request, search: Optional[str] = None, page: int = 1, page_size: int = 20):
    qs = Product.objects.all()
    if search:
        qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search) | Q(brand__icontains=search))
    qs = qs.order_by("name")[(page - 1) * page_size : page * page_size]
    return [ProductOut.from_orm(p) for p in qs]

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
        return ProductOut.from_orm(p)
    except Product.DoesNotExist:
        return 404, {"error": "NOT_FOUND", "message": "producto no encontrado"}

@router.get("/ping")
def ping(request) -> dict:
    """Simple endpoint used for smoke testing the catalog API."""
    return {"message": "catalog pong"}

