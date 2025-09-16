from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import F, Count
from datetime import timedelta

from apps.stock.models import Movement, StockLot
from apps.orders.models import Order
from apps.notifications.models import Notification
from apps.notifications.services import generate_low_stock_alerts, generate_near_expiry_alerts
from .security import scope_required

@login_required
@scope_required('dashboard')
def ops_feed(request):
    """Feed de operaciones del sistema con información en tiempo real."""
    try:
        # Obtener alertas del sistema (últimas notificaciones)
        alerts = Notification.objects.filter(
            event__in=['low_stock', 'near_expiry']
        ).order_by('-created_at')[:10]
        
        # Movimientos de stock recientes (últimas 24 horas)
        yesterday = timezone.now() - timedelta(days=1)
        recent_stock_movements = Movement.objects.filter(
            created_at__gte=yesterday
        ).select_related('product', 'created_by').order_by('-created_at')[:15]
        
        # Pedidos recientes (últimos 7 días)
        week_ago = timezone.now() - timedelta(days=7)
        recent_orders = Order.objects.filter(
            created_at__gte=week_ago
        ).select_related('customer').order_by('-created_at')[:10]
        
        # Productos próximos a vencer (próximos 30 días)
        next_month = timezone.now() + timedelta(days=30)
        expiring_products = StockLot.objects.filter(
            expiry_date__lte=next_month.date(),
            expiry_date__gte=timezone.now().date(),
            qty_on_hand__gt=0
        ).select_related('product').order_by('expiry_date')[:10]
        
        # Estadísticas rápidas
        stats = {
            'total_products': StockLot.objects.filter(qty_on_hand__gt=0).count(),
            'pending_orders': Order.objects.filter(status='pending').count(),
            'low_stock_products': StockLot.objects.filter(
                qty_on_hand__lte=5  # Umbral por defecto
            ).count(),
            'active_customers': Order.objects.values('customer').distinct().count()
        }
        
        context = {
            'alerts': alerts,
            'recent_stock_movements': recent_stock_movements,
            'recent_orders': recent_orders,
            'expiring_products': expiring_products,
            'stats': stats,
        }
        
        return render(request, 'panel/ops_feed.html', context)
        
    except Exception as e:
        # Log del error y mostrar página con mensaje de error
        context = {
            'error': 'Error al cargar el feed de operaciones',
            'alerts': [],
            'recent_stock_movements': [],
            'recent_orders': [],
            'expiring_products': [],
            'stats': {}
        }
        return render(request, 'panel/ops_feed.html', context)