"""
API endpoints para autenticación JWT con rate limiting.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.exceptions import TokenError
import json
import structlog

logger = structlog.get_logger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login(request):
    """
    Endpoint de login con JWT y rate limiting.
    Rate limit: 5 intentos por minuto por IP.
    """
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            logger.warning("login_attempt_missing_credentials", 
                         remote_addr=request.META.get('REMOTE_ADDR'))
            return JsonResponse({
                'error': 'MISSING_CREDENTIALS',
                'message': 'Username and password are required'
            }, status=400)
        
        # Autenticar usuario
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                # Generar tokens JWT
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                logger.info("login_successful", 
                          user_id=user.id, 
                          username=user.username,
                          remote_addr=request.META.get('REMOTE_ADDR'))
                
                return JsonResponse({
                    'access': str(access_token),
                    'refresh': str(refresh),
                }, status=200)
            else:
                logger.warning("login_attempt_inactive_user", 
                             username=username,
                             remote_addr=request.META.get('REMOTE_ADDR'))
                return JsonResponse({
                    'error': 'INACTIVE_USER',
                    'message': 'User account is disabled'
                }, status=401)
        else:
            logger.warning("login_attempt_invalid_credentials", 
                         username=username,
                         remote_addr=request.META.get('REMOTE_ADDR'))
            return JsonResponse({
                'error': 'INVALID_CREDENTIALS',
                'message': 'Invalid username or password'
            }, status=401)
            
    except json.JSONDecodeError:
        logger.warning("login_attempt_invalid_json", 
                     remote_addr=request.META.get('REMOTE_ADDR'))
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error("login_error", 
                   error=str(e),
                   remote_addr=request.META.get('REMOTE_ADDR'))
        return JsonResponse({
            'error': 'INTERNAL_ERROR',
            'message': 'An internal error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def refresh_token_api(request):
    """
    Endpoint para refrescar tokens JWT.
    Implementa refresh rotativo y blacklisting.
    """
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh')
        
        if not refresh_token:
            return JsonResponse({
                'error': 'MISSING_REFRESH_TOKEN',
                'message': 'Refresh token is required'
            }, status=400)
        
        try:
            # Crear nuevo refresh token (rotativo)
            token = RefreshToken(refresh_token)
            
            # Obtener el usuario del token
            user_id = token.payload['user_id']
            user = User.objects.get(id=user_id)
            
            # Generar nuevos tokens
            new_refresh = RefreshToken.for_user(user)
            new_access = new_refresh.access_token
            
            # El token anterior se blacklistea automáticamente por BLACKLIST_AFTER_ROTATION
            
            logger.info("token_refresh_successful", 
                      user_id=user_id,
                      remote_addr=request.META.get('REMOTE_ADDR'))
            
            return JsonResponse({
                'access': str(new_access),
            }, status=200)
            
        except TokenError as e:
            logger.warning("token_refresh_invalid", 
                         error=str(e),
                         remote_addr=request.META.get('REMOTE_ADDR'))
            return JsonResponse({
                'error': 'INVALID_TOKEN',
                'message': 'Invalid or expired refresh token'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error("token_refresh_error", 
                   error=str(e),
                   remote_addr=request.META.get('REMOTE_ADDR'))
        return JsonResponse({
            'error': 'INTERNAL_ERROR',
            'message': 'An internal error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_api(request):
    """
    Endpoint de logout que blacklistea el refresh token.
    """
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return JsonResponse({
                'error': 'MISSING_REFRESH_TOKEN',
                'message': 'Refresh token is required'
            }, status=400)
        
        try:
            # Blacklistear el refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            logger.info("logout_successful", 
                      user_id=token.payload['user_id'],
                      remote_addr=request.META.get('REMOTE_ADDR'))
            
            return JsonResponse({
                'message': 'Successfully logged out'
            }, status=200)
            
        except TokenError as e:
            logger.warning("logout_invalid_token", 
                         error=str(e),
                         remote_addr=request.META.get('REMOTE_ADDR'))
            return JsonResponse({
                'error': 'INVALID_TOKEN',
                'message': 'Invalid refresh token'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'INVALID_JSON',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error("logout_error", 
                   error=str(e),
                   remote_addr=request.META.get('REMOTE_ADDR'))
        return JsonResponse({
            'error': 'INTERNAL_ERROR',
            'message': 'An internal error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def me(request):
    """
    Endpoint para obtener información del usuario autenticado.
    Requiere token JWT válido en el header Authorization.
    """
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    
    try:
        # Extraer token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'MISSING_TOKEN',
                'message': 'Authorization header with Bearer token is required'
            }, status=401)
        
        # Validar token JWT
        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
            user = jwt_auth.get_user(validated_token)
        except (InvalidToken, TokenError) as e:
            logger.warning("me_endpoint_invalid_token", 
                         error=str(e),
                         remote_addr=request.META.get('REMOTE_ADDR'))
            return JsonResponse({
                'error': 'INVALID_TOKEN',
                'message': 'Invalid or expired token'
            }, status=401)
        
        # Obtener información adicional del usuario
        try:
            from apps.customers.models import Customer
            # Buscar si el usuario tiene un customer asociado por email
            customer = None
            if user.email:
                try:
                    customer = Customer.objects.get(email=user.email)
                except Customer.DoesNotExist:
                    pass
            
            # Obtener scope del usuario si existe
            user_scope = None
            if hasattr(user, 'scope'):
                scope = user.scope
                user_scope = {
                    'has_scope_users': scope.has_scope_users,
                    'has_scope_dashboard': scope.has_scope_dashboard,
                    'has_scope_inventory': scope.has_scope_inventory,
                    'has_scope_orders': scope.has_scope_orders,
                    'has_scope_customers': scope.has_scope_customers,
                    'has_scope_reports': scope.has_scope_reports,
                    'has_scope_analytics': scope.has_scope_analytics,
                }
            
            # Obtener roles del usuario según B0-BE-02
            roles = []
            if user.is_superuser:
                roles = ['admin']
            elif hasattr(user, 'scope') and hasattr(user.scope, 'roles'):
                # Obtener roles específicos del modelo Role
                user_roles = user.scope.roles.filter(is_active=True)
                roles = [role.name for role in user_roles]
            elif user.is_staff:
                roles = ['admin']  # Staff por defecto es admin
            else:
                roles = []  # Usuario sin roles específicos

            response_data = {
                'id': user.id,
                'username': user.username,
                'roles': roles,
            }
            
            
            logger.info("me_endpoint_successful", 
                      user_id=user.id,
                      username=user.username,
                      remote_addr=request.META.get('REMOTE_ADDR'))
            
            return JsonResponse(response_data, status=200)
            
        except Exception as e:
            logger.error("me_endpoint_data_error", 
                       user_id=user.id,
                       error=str(e),
                       remote_addr=request.META.get('REMOTE_ADDR'))
            # Devolver información básica del usuario en caso de error
            roles = ['admin'] if user.is_superuser else []
            return JsonResponse({
                'id': user.id,
                'username': user.username,
                'roles': roles,
            }, status=200)
            
    except Exception as e:
        logger.error("me_endpoint_error", 
                   error=str(e),
                   remote_addr=request.META.get('REMOTE_ADDR'))
        return JsonResponse({
            'error': 'INTERNAL_ERROR',
            'message': 'An internal error occurred'
        }, status=500)


# Aliases for URL mapping
refresh_token = refresh_token_api
logout = logout_api