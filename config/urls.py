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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from api import api
from apps.core.health import health_live, health_ready
from apps.core.metrics_api import metrics_endpoint
from apps.core.views import sentry_test_error
from apps.stock.views import stock_detail
from apps.core.b2b_views import home as b2b_home, cart as b2b_cart, checkout as b2b_checkout
from apps.pos.views import pos_interface, pos_history, pos_sale_detail, pos_sale_lots_csv
from django.http import HttpResponseRedirect

def redirect_to_panel_login(request):
    return redirect('panel:login')

def redirect_to_custom_pos(request):
    """Redirige al POS personalizado del usuario"""
    return HttpResponseRedirect('http://localhost:5173/')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # JWT Authentication API (debe ir ANTES que Django Ninja API)
    path('api/', include('apps.core.urls')),
    
    # Django Ninja API
    path('api/v1/', api.urls),
    
    # Metrics endpoints
    path('', include('django_prometheus.urls')),
    path('api/v1/metrics/', metrics_endpoint, name='cache_metrics'),
    
    # Health endpoints
    path('health/live/', health_live, name='health_live'),
    path('health/ready/', health_ready, name='health_ready'),
    
    # Sentry test endpoint
    path('sentry-test/', sentry_test_error, name='sentry_test_error'),
    
    # Authentication
    path('accounts/login/', redirect_to_panel_login, name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Panel and POS
    path('panel/', include('apps.panel.urls')),
    path('panel/stock/<int:product_id>/', stock_detail, name='panel_stock_detail'),
    path('pos/', redirect_to_custom_pos, name='pos_interface'),
    path('pos/history/', redirect_to_custom_pos, name='pos_history'),
    path('pos/sale/<str:sale_id>/', pos_sale_detail, name='pos_sale_detail'),
    path('pos/sale/<str:sale_id>/lots.csv', pos_sale_lots_csv, name='pos_sale_lots_csv'),
    
    # B2B
    path('b2b/', b2b_home, name='b2b_home'),
    path('b2b/cart/', b2b_cart, name='b2b_cart'),
    path('b2b/checkout/', b2b_checkout, name='b2b_checkout'),
]
