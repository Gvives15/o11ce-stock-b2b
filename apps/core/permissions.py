"""
Decoradores de permisos para endpoints sensibles basados en roles B0-BE-02.
"""
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import structlog

logger = structlog.get_logger(__name__)


def get_user_roles(user):
    """Obtiene los roles de un usuario."""
    if user.is_superuser:
        return ['admin']
    elif hasattr(user, 'scope') and hasattr(user.scope, 'roles'):
        return [role.name for role in user.scope.roles.filter(is_active=True)]
    elif user.is_staff:
        return ['admin']
    else:
        return []


def role_required(required_roles):
    """
    Decorador que requiere que el usuario tenga uno de los roles especificados.
    
    Args:
        required_roles: Lista de roles requeridos (ej: ['admin', 'vendedor_caja'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Extraer token JWT del header
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JsonResponse({
                    'error': 'MISSING_TOKEN',
                    'message': 'Authorization header with Bearer token is required'
                }, status=401)
            
            try:
                # Validar token JWT
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
                user = jwt_auth.get_user(validated_token)
                
                # Obtener roles del usuario
                user_roles = get_user_roles(user)
                
                # Verificar si el usuario tiene alguno de los roles requeridos
                if not any(role in user_roles for role in required_roles):
                    logger.warning("role_permission_denied", 
                                 user_id=user.id,
                                 username=user.username,
                                 user_roles=user_roles,
                                 required_roles=required_roles,
                                 remote_addr=request.META.get('REMOTE_ADDR'))
                    return JsonResponse({
                        'error': 'INSUFFICIENT_PERMISSIONS',
                        'message': f'Required roles: {", ".join(required_roles)}'
                    }, status=403)
                
                # Agregar usuario y roles al request para uso en la vista
                request.user_roles = user_roles
                
                return view_func(request, *args, **kwargs)
                
            except (InvalidToken, TokenError) as e:
                logger.warning("role_decorator_invalid_token", 
                             error=str(e),
                             remote_addr=request.META.get('REMOTE_ADDR'))
                return JsonResponse({
                    'error': 'INVALID_TOKEN',
                    'message': 'Invalid or expired token'
                }, status=401)
            except Exception as e:
                logger.error("role_decorator_error", 
                           error=str(e),
                           remote_addr=request.META.get('REMOTE_ADDR'))
                return JsonResponse({
                    'error': 'INTERNAL_ERROR',
                    'message': 'An internal error occurred'
                }, status=500)
        
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorador que requiere rol de administrador."""
    return role_required(['admin'])(view_func)


def vendedor_required(view_func):
    """Decorador que requiere rol de vendedor (caja o ruta)."""
    return role_required(['vendedor_caja', 'vendedor_ruta'])(view_func)


def vendedor_caja_required(view_func):
    """Decorador que requiere rol específico de vendedor de caja."""
    return role_required(['vendedor_caja'])(view_func)


def vendedor_ruta_required(view_func):
    """Decorador que requiere rol específico de vendedor de ruta."""
    return role_required(['vendedor_ruta'])(view_func)


def pos_operation_required(view_func):
    """
    Decorador para operaciones sensibles del POS.
    Requiere admin o vendedor_caja.
    """
    return role_required(['admin', 'vendedor_caja'])(view_func)


def cancellation_required(view_func):
    """
    Decorador para operaciones de anulación.
    Requiere admin o vendedor_caja.
    """
    return role_required(['admin', 'vendedor_caja'])(view_func)
