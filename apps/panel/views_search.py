from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from django.http import JsonResponse
from .security import scope_required, has_scope
from apps.catalog.models import Product
from apps.orders.models import Order
from apps.customers.models import Customer
from apps.stock.models import StockLot

@login_required
def global_search(request):
    """Vista para búsqueda global en el panel"""
    query = request.GET.get('q', '').strip()
    results = {
        'products': [],
        'orders': [],
        'customers': [],
        'stock': []
    }
    
    if len(query) >= 2:  # Mínimo 2 caracteres para buscar
        # Buscar productos (si tiene acceso a inventario)
        if has_scope(request.user, 'inventory'):
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(sku__icontains=query)
            )[:5]
            results['products'] = [{
                'id': p.id,
                'name': p.name,
                'sku': p.sku,
                'price': float(p.price),
                'url': f'/panel/inventory/{p.id}/'
            } for p in products]
        
        # Buscar pedidos (si tiene acceso a pedidos)
        if has_scope(request.user, 'orders'):
            orders = Order.objects.filter(
                Q(id__icontains=query)
            )[:5]
            results['orders'] = [{
                'id': o.id,
                'customer': o.customer.name if o.customer else 'Sin cliente',
                'total': float(o.total),
                'status': o.status,
                'url': f'/panel/orders/{o.id}/'
            } for o in orders]
        
        # Buscar clientes (si tiene acceso a clientes)
        if has_scope(request.user, 'customers'):
            customers = Customer.objects.filter(
                Q(name__icontains=query) | Q(email__icontains=query)
            )[:5]
            results['customers'] = [{
                'id': c.id,
                'name': c.name,
                'email': c.email,
                'segment': c.segment,
                'url': f'/panel/customers/{c.id}/'
            } for c in customers]
        
        # Buscar stock (si tiene acceso a inventario)
        if has_scope(request.user, 'inventory'):
            stock_lots = StockLot.objects.select_related('product').filter(
                Q(product__name__icontains=query) | 
                Q(product__sku__icontains=query) |
                Q(lot_code__icontains=query)
            )[:5]
            results['stock'] = [{
                'id': s.id,
                'product_name': s.product.name,
                'lot_code': s.lot_code,
                'quantity': s.quantity,
                'expiry_date': s.expiry_date.strftime('%Y-%m-%d') if s.expiry_date else None,
                'url': f'/panel/stock/{s.id}/'
            } for s in stock_lots]
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(results)
    
    return render(request, 'panel/search_results.html', {
        'query': query,
        'results': results
    })

@login_required
def search_suggestions(request):
    """API endpoint para sugerencias de búsqueda en tiempo real"""
    query = request.GET.get('q', '').strip()
    suggestions = []
    
    if len(query) >= 2:
        # Productos
        if has_scope(request.user, 'inventory'):
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(sku__icontains=query)
            )[:3]
            for p in products:
                suggestions.append({
                    'type': 'product',
                    'label': f'{p.name} ({p.sku})',
                    'value': p.name,
                    'url': f'/panel/inventory/{p.id}/'
                })
        
        # Clientes
        if has_scope(request.user, 'customers'):
            customers = Customer.objects.filter(
                Q(name__icontains=query) | Q(email__icontains=query)
            )[:3]
            for c in customers:
                suggestions.append({
                    'type': 'customer',
                    'label': f'{c.name} ({c.email})',
                    'value': c.name,
                    'url': f'/panel/customers/{c.id}/'
                })
    
    return JsonResponse({'suggestions': suggestions})