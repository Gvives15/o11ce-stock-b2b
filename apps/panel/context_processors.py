from .security import has_scope

def navigation_context(request):
    """Context processor para navegación del panel."""
    context = {
        'has_scope': lambda scope: has_scope(request.user, scope) if request.user.is_authenticated else False,
        'navigation_items': []
    }
    
    if request.user.is_authenticated:
        # Dashboard - siempre visible para usuarios autenticados
        if has_scope(request.user, 'dashboard'):
            context['navigation_items'].append({
                'name': 'Dashboard',
                'url': 'panel:dashboard',
                'icon': 'fas fa-tachometer-alt',
                'active': request.resolver_match.url_name == 'dashboard'
            })
        
        # Inventario
        if has_scope(request.user, 'inventory'):
            context['navigation_items'].append({
                'name': 'Inventario',
                'url': 'panel:stock_list',
                'icon': 'fas fa-boxes',
                'active': request.resolver_match.url_name in ['stock_list', 'stock_detail']
            })
        
        # Pedidos
        if has_scope(request.user, 'orders'):
            context['navigation_items'].append({
                'name': 'Pedidos',
                'url': 'panel:orders_list',
                'icon': 'fas fa-shopping-cart',
                'active': request.resolver_match.url_name in ['orders_list', 'order_detail']
            })
        
        # Clientes
        if has_scope(request.user, 'customers'):
            context['navigation_items'].append({
                'name': 'Clientes',
                'url': 'panel:customers_list',
                'icon': 'fas fa-users',
                'active': request.resolver_match.url_name in ['customers_list', 'customer_detail']
            })
        
        # Reportes
        if has_scope(request.user, 'reports'):
            context['navigation_items'].append({
                'name': 'Reportes',
                'url': 'panel:reports',
                'icon': 'fas fa-chart-bar',
                'active': request.resolver_match.url_name == 'reports'
            })
        
        # Analytics
        if has_scope(request.user, 'analytics'):
            context['navigation_items'].append({
                'name': 'Analytics',
                'url': 'panel:analytics',
                'icon': 'fas fa-chart-line',
                'active': request.resolver_match.url_name == 'analytics'
            })
        
        # Usuarios (solo admin)
        if has_scope(request.user, 'users'):
            context['navigation_items'].append({
                'name': 'Usuarios',
                'url': 'panel:users_list',
                'icon': 'fas fa-user-cog',
                'active': request.resolver_match.url_name in ['users_list']
            })
        
        # Variables específicas de scope para templates
        context.update({
            'has_scope_users': has_scope(request.user, 'users'),
            'has_scope_dashboard': has_scope(request.user, 'dashboard'),
            'has_scope_inventory': has_scope(request.user, 'inventory'),
            'has_scope_orders': has_scope(request.user, 'orders'),
            'has_scope_customers': has_scope(request.user, 'customers'),
            'has_scope_reports': has_scope(request.user, 'reports'),
            'has_scope_analytics': has_scope(request.user, 'analytics'),
        })
    
    return context