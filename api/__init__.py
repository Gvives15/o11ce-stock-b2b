"""Root API configuration for the project.""" 

from django.http import HttpRequest
from ninja import NinjaAPI

from apps.core.api import router as core_router
from apps.catalog.api import router as catalog_router
from apps.stock.api import router as stock_router
from apps.stock.api_stock import router as stock_detail_router
from apps.stock.api_movements import router as movements_router
from apps.customers.api import router as customers_router
from apps.orders.api import router as orders_router
from apps.notifications.api import router as notifications_router
from apps.pos.api import router as pos_router

# Configuración completa de Django Ninja API
api = NinjaAPI(
    title="BFF API",
    version="1.0.0",
    description="""
    # API Backend For Frontend (BFF)
    
    Esta API proporciona endpoints para gestionar:
    
    ## 📦 Catálogo de Productos
    - Crear, listar, obtener y actualizar productos
    - Búsqueda por código, nombre o marca
    - Paginación de resultados
    
    ## 📊 Gestión de Stock
    - Entrada de stock con lotes
    - Salida FEFO (First Expired, First Out)
    - Consulta de inventario por producto
    
    ## 🛒 Órdenes y Checkout
    - Procesamiento de pedidos
    - Checkout con validación de stock
    - Gestión de direcciones de entrega
    
    ## 🏪 POS (Point of Sale)
    - Ventas con soporte FEFO automático
    - Override de lotes con justificación
    - Transacciones atómicas
    
    ## 👥 Clientes
    - Gestión de información de clientes
    - Direcciones y datos de contacto
    
    ## 🔔 Notificaciones
    - Sistema de notificaciones
    - Diferentes canales de comunicación
    
    ## 🔧 Core
    - Endpoints de utilidad y monitoreo
    - Health checks y ping
    
    ---
    
    **Versión:** 1.0.0  
    **Entorno:** Desarrollo  
    **Documentación:** Swagger UI disponible en `/docs`
    """,
    docs_url="/docs",
    openapi_url="/openapi.json",
    urls_namespace="main_api"
)

api.add_router("/core", core_router)
api.add_router("/catalog", catalog_router)
api.add_router("/stock", stock_router)
api.add_router("/orders", orders_router)
api.add_router("/notifications", notifications_router)
api.add_router("/customers", customers_router)
api.add_router("", stock_detail_router)
api.add_router("/movements", movements_router)
api.add_router("/pos", pos_router)

__all__ = ["api"]
