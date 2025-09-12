"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from apps.core.api import router as core_router
from apps.catalog.api import router as catalog_router
from apps.customers.api import router as customers_router
from apps.orders.api import router as orders_router
from apps.stock.api import router as stock_router
from apps.notifications.api import router as notifications_router

api = NinjaAPI(title="O11CE Stock B2B API")

# Registrar los routers de cada aplicación
api.add_router("/core/", core_router)
api.add_router("/catalog/", catalog_router)
api.add_router("/customers/", customers_router)
api.add_router("/orders/", orders_router)
api.add_router("/stock/", stock_router)
api.add_router("/notifications/", notifications_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
]
