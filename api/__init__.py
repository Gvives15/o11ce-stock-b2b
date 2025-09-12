"""Root API configuration for the project."""

from ninja import NinjaAPI

from apps.core.api import router as core_router
from apps.catalog.api import router as catalog_router
from apps.stock.api import router as stock_router
from apps.orders.api import router as orders_router
from apps.notifications.api import router as notifications_router
from apps.customers.api import router as customers_router

api = NinjaAPI()

api.add_router("/core", core_router)
api.add_router("/catalog", catalog_router)
api.add_router("/stock", stock_router)
api.add_router("/orders", orders_router)
api.add_router("/notifications", notifications_router)
api.add_router("/customers", customers_router)

__all__ = ["api"]
