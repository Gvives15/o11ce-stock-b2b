from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def has_scope(user, scope_key):
    """Verifica si un usuario tiene un scope específico basado en UserScope."""
    if not user.is_authenticated:
        return False
    
    # Los superusuarios tienen acceso a todo
    if user.is_superuser:
        return True
    
    # Verificar si el usuario tiene UserScope
    if not hasattr(user, 'scope'):
        return False
    
    # Mapear scope_key a campo del modelo
    scope_field = f"has_scope_{scope_key}"
    return getattr(user.scope, scope_field, False)

def scope_required(required_scope):
    """Decorador que requiere un scope específico"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('panel:login')
            
            if not has_scope(request.user, required_scope):
                return HttpResponseForbidden(
                    f"No tienes permisos para acceder a esta sección. Scope requerido: {required_scope}"
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def multiple_scopes_required(*required_scopes):
    """Decorador que requiere múltiples scopes (OR logic)"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('panel:login')
            
            # Verificar si el usuario tiene al menos uno de los scopes requeridos
            if not any(has_scope(request.user, scope) for scope in required_scopes):
                return HttpResponseForbidden(
                    f"No tienes permisos para acceder a esta sección. Scopes requeridos: {', '.join(required_scopes)}"
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Definición de scopes por rol para migración (opcional)
ROLE_SCOPE_MATRIX = {
    'admin': {
        'has_scope_users': True,
        'has_scope_dashboard': True,
        'has_scope_inventory': True,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_reports': True,
        'has_scope_analytics': True,
    },
    'encargado_inventario': {
        'has_scope_users': False,
        'has_scope_dashboard': True,
        'has_scope_inventory': True,
        'has_scope_orders': True,
        'has_scope_customers': False,
        'has_scope_reports': True,
        'has_scope_analytics': False,
    },
    'vendedor_caja': {
        'has_scope_users': False,
        'has_scope_dashboard': True,
        'has_scope_inventory': False,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_reports': False,
        'has_scope_analytics': False,
    },
    'vendedor_ruta': {
        'has_scope_users': False,
        'has_scope_dashboard': True,
        'has_scope_inventory': False,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_reports': False,
        'has_scope_analytics': False,
    }
}