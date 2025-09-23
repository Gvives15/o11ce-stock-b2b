"""Root API configuration for the project.""" 

from django.http import HttpRequest
from ninja import NinjaAPI

# Core & System
from apps.core.api import router as core_router

# Product Management
from apps.catalog.api import router as catalog_router

# Inventory & Stock Management
from apps.stock.api import router as stock_router
from apps.stock.api_stock import router as stock_detail_router
from apps.stock.api_movements import router as movements_router

# Customer & Order Management
from apps.customers.api import router as customers_router
from apps.orders.api import router as orders_router
from apps.orders.picking_api import picking_router

# Point of Sale
from apps.pos.api import router as pos_router

# Panel Administrativo
from apps.panel.api import panel_router

# Communication & Notifications
from apps.notifications.api import router as notifications_router

# Configuración completa de Django Ninja API
api = NinjaAPI(
    title="BFF API",
    version="1.0.0",
    description="""
    # API Backend For Frontend (BFF)
    
    Esta API proporciona endpoints organizados por funcionalidad:
    
    ## 🔧 Core & System
    - Health checks y monitoreo del sistema
    - Endpoints de utilidad y diagnóstico
    
    ## 📦 Product Management
    - **Catálogo de Productos**: Crear, listar, obtener y actualizar productos
    - **Búsqueda Avanzada**: Por código, nombre o marca con paginación
    
    ## 📊 Inventory & Stock Management
    - **Gestión de Stock**: Entrada de stock con lotes y fechas de vencimiento
    - **Sistema FEFO**: First Expired, First Out automático
    - **Movimientos**: Trazabilidad completa de inventario
    - **Consultas**: Inventario por producto y disponibilidad
    
    ## 👥 Customer & Order Management
    - **Clientes**: Gestión completa de información y direcciones
    - **Órdenes**: Procesamiento de pedidos con validación de stock
    - **Checkout**: Sistema de checkout con gestión de direcciones
    
    ## 🏪 Point of Sale (POS)
    - **Ventas**: Sistema POS con soporte FEFO automático
    - **Override de Lotes**: Con justificación y trazabilidad
    - **Transacciones**: Operaciones atómicas y seguras
    
    ## 🔔 Communication & Notifications
    - **Notificaciones**: Sistema multi-canal de comunicación
    - **Alertas**: Gestión de eventos y notificaciones automáticas
    
    ---
    
    **Versión:** 1.0.0  
    **Entorno:** Desarrollo  
    **Documentación:** Swagger UI disponible en `/docs`
    
    > 💡 **Tip**: Los endpoints están organizados por grupos funcionales para facilitar la navegación
    """,
    docs_url="/docs",
    openapi_url="/openapi.json",
    urls_namespace="main_api"
)

# Registro de routers en orden lógico de funcionalidad

# 1. Core & System - Funcionalidades básicas del sistema
api.add_router("/core", core_router)

# 2. Product Management - Gestión de productos
api.add_router("/catalog", catalog_router)

# 3. Inventory & Stock Management - Gestión de inventario
api.add_router("/stock", stock_router)
api.add_router("", stock_detail_router)  # Endpoints de stock detallado en raíz
api.add_router("/movements", movements_router)

# 4. Customer & Order Management - Gestión de clientes y pedidos
api.add_router("/customers", customers_router)
api.add_router("/orders", orders_router)
api.add_router("/orders", picking_router)  # Picking endpoints under /orders

# 5. Point of Sale - Sistema de ventas
api.add_router("/pos", pos_router)

# 6. Panel Administrativo - Gestión del panel
api.add_router("/panel/v1", panel_router)

# 7. Communication & Notifications - Comunicaciones
api.add_router("/notifications", notifications_router)

__all__ = ["api"]
