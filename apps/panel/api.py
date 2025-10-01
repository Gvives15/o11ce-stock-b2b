"""API Router para el panel administrativo
Protegido por permisos panel_access
"""

from ninja import Router
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.core.exceptions import PermissionDenied

from .orders_api import orders_router
from .users_api import users_router
from .schemas import UserMeSchema, UserScopeSchema

class JWTAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
        try:
            # Usar JWTAuthentication de DRF para validar el token
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            
            return user
            
        except (InvalidToken, TokenError):
            return None

def check_panel_permission(request):
    """Verificar permiso panel_access"""
    if not request.auth.has_perm('auth.panel_access'):
        raise PermissionDenied("No tienes permisos para acceder al panel")

# Router principal del panel
panel_router = Router(auth=JWTAuth())

# Incluir sub-routers
panel_router.add_router("/orders", orders_router)
panel_router.add_router("/users", users_router)

@panel_router.get("/health")
def panel_health(request):
    """Health check del panel"""
    check_panel_permission(request)
    return {"status": "ok", "service": "panel"}


@panel_router.get("/me", response=UserMeSchema)
def get_current_user(request):
    """Obtener información del usuario actual"""
    user = request.auth
    
    # Obtener scopes del usuario
    user_scope = getattr(user, 'scope', None)
    if not user_scope:
        # Si no tiene scope, crear uno por defecto
        from .models import UserScope
        user_scope = UserScope.objects.create(user=user)
    
    # Obtener roles del usuario
    roles = list(user_scope.roles.values_list('name', flat=True))
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "date_joined": user.date_joined,
        "last_login": user.last_login,
        "scopes": {
            "has_scope_users": user_scope.has_scope_users,
            "has_scope_dashboard": user_scope.has_scope_dashboard,
            "has_scope_inventory": user_scope.has_scope_inventory,
            "has_scope_inventory_level_1": user_scope.has_scope_inventory_level_1,
            "has_scope_inventory_level_2": user_scope.has_scope_inventory_level_2,
            "has_scope_orders": user_scope.has_scope_orders,
            "has_scope_customers": user_scope.has_scope_customers,
            "has_scope_reports": user_scope.has_scope_reports,
            "has_scope_analytics": user_scope.has_scope_analytics,
            "has_scope_catalog": user_scope.has_scope_catalog,
            "has_scope_caja": user_scope.has_scope_caja,
            "has_scope_pos_override": user_scope.has_scope_pos_override,
        },
        "roles": roles
    }