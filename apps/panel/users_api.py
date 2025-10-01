"""API REST para gestión de usuarios del panel administrativo"""

from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db import transaction
from ninja import Router, Schema
from ninja.security import HttpBearer
from ninja.errors import HttpError
from typing import List, Optional
import logging

from .models import UserScope
from .security import has_scope

logger = logging.getLogger(__name__)

users_router = Router()

# Schemas
class UserCreateSchema(Schema):
    username: str
    email: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    password: str
    groups: Optional[List[int]] = []
    is_active: bool = True
    # Scopes
    has_scope_dashboard: bool = True
    has_scope_inventory: bool = False
    has_scope_orders: bool = False
    has_scope_customers: bool = False
    has_scope_reports: bool = False
    has_scope_analytics: bool = False
    has_scope_users: bool = False

class UserUpdateSchema(Schema):
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    groups: Optional[List[int]] = None
    is_active: Optional[bool] = None
    # Scopes
    has_scope_dashboard: Optional[bool] = None
    has_scope_inventory: Optional[bool] = None
    has_scope_orders: Optional[bool] = None
    has_scope_customers: Optional[bool] = None
    has_scope_reports: Optional[bool] = None
    has_scope_analytics: Optional[bool] = None
    has_scope_users: Optional[bool] = None

class UserResponseSchema(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    date_joined: str
    last_login: Optional[str] = None
    groups: List[str]
    # Scopes
    has_scope_dashboard: bool
    has_scope_inventory: bool
    has_scope_orders: bool
    has_scope_customers: bool
    has_scope_reports: bool
    has_scope_analytics: bool
    has_scope_users: bool

class UserListResponseSchema(Schema):
    users: List[UserResponseSchema]
    total: int

class GroupSchema(Schema):
    id: int
    name: str

def check_users_permission(request):
    """Verificar que el usuario tenga permisos para gestionar usuarios"""
    if not request.auth:
        raise HttpError(401, "Authentication required")
    
    if not has_scope(request.auth, 'users'):
        raise HttpError(403, "No tienes permisos para gestionar usuarios")

def serialize_user(user: User) -> dict:
    """Serializar un usuario con sus scopes"""
    user_scope = getattr(user, 'scope', None)
    if not user_scope:
        # Crear UserScope si no existe
        user_scope = UserScope.objects.create(user=user, has_scope_dashboard=True)
    
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_active': user.is_active,
        'date_joined': user.date_joined.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'groups': [group.name for group in user.groups.all()],
        'has_scope_dashboard': user_scope.has_scope_dashboard,
        'has_scope_inventory': user_scope.has_scope_inventory,
        'has_scope_orders': user_scope.has_scope_orders,
        'has_scope_customers': user_scope.has_scope_customers,
        'has_scope_reports': user_scope.has_scope_reports,
        'has_scope_analytics': user_scope.has_scope_analytics,
        'has_scope_users': user_scope.has_scope_users,
    }

@users_router.get("/", response=UserListResponseSchema)
def list_users(request):
    """Listar todos los usuarios"""
    check_users_permission(request)
    
    users = User.objects.all().select_related('scope').prefetch_related('groups')
    serialized_users = [serialize_user(user) for user in users]
    
    return UserListResponseSchema(
        users=serialized_users,
        total=len(serialized_users)
    )

@users_router.post("/", response=UserResponseSchema)
def create_user(request, data: UserCreateSchema):
    """Crear un nuevo usuario"""
    check_users_permission(request)
    
    try:
        with transaction.atomic():
            # Validaciones
            if User.objects.filter(username=data.username).exists():
                raise HttpError(400, f"Ya existe un usuario con el nombre '{data.username}'")
            
            if User.objects.filter(email=data.email).exists():
                raise HttpError(400, f"Ya existe un usuario con el email '{data.email}'")
            
            # Crear usuario
            user = User.objects.create_user(
                username=data.username,
                email=data.email,
                password=data.password,
                first_name=data.first_name,
                last_name=data.last_name,
                is_active=data.is_active
            )
            
            # Asignar grupos
            if data.groups:
                groups = Group.objects.filter(id__in=data.groups)
                user.groups.set(groups)
            
            # Configurar scopes
            user_scope, created = UserScope.objects.get_or_create(user=user)
            user_scope.has_scope_dashboard = data.has_scope_dashboard
            user_scope.has_scope_inventory = data.has_scope_inventory
            user_scope.has_scope_orders = data.has_scope_orders
            user_scope.has_scope_customers = data.has_scope_customers
            user_scope.has_scope_reports = data.has_scope_reports
            user_scope.has_scope_analytics = data.has_scope_analytics
            user_scope.has_scope_users = data.has_scope_users
            user_scope.save()
            
            logger.info(f"Usuario '{user.username}' creado por {request.auth.username}")
            
            return serialize_user(user)
            
    except ValidationError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Error creando usuario: {str(e)}")
        raise HttpError(500, "Error interno del servidor")

@users_router.get("/{user_id}", response=UserResponseSchema)
def get_user(request, user_id: int):
    """Obtener detalles de un usuario"""
    check_users_permission(request)
    
    user = get_object_or_404(User, id=user_id)
    return serialize_user(user)

@users_router.put("/{user_id}", response=UserResponseSchema)
def update_user(request, user_id: int, data: UserUpdateSchema):
    """Actualizar un usuario existente"""
    check_users_permission(request)
    
    try:
        with transaction.atomic():
            user = get_object_or_404(User, id=user_id)
            
            # Actualizar campos básicos
            if data.username is not None:
                if User.objects.filter(username=data.username).exclude(id=user_id).exists():
                    raise HttpError(400, f"Ya existe un usuario con el nombre '{data.username}'")
                user.username = data.username
            
            if data.email is not None:
                if User.objects.filter(email=data.email).exclude(id=user_id).exists():
                    raise HttpError(400, f"Ya existe un usuario con el email '{data.email}'")
                user.email = data.email
            
            if data.first_name is not None:
                user.first_name = data.first_name
            
            if data.last_name is not None:
                user.last_name = data.last_name
            
            if data.password is not None:
                user.set_password(data.password)
            
            if data.is_active is not None:
                user.is_active = data.is_active
            
            user.save()
            
            # Actualizar grupos
            if data.groups is not None:
                groups = Group.objects.filter(id__in=data.groups)
                user.groups.set(groups)
            
            # Actualizar scopes
            user_scope, created = UserScope.objects.get_or_create(user=user)
            
            if data.has_scope_dashboard is not None:
                user_scope.has_scope_dashboard = data.has_scope_dashboard
            if data.has_scope_inventory is not None:
                user_scope.has_scope_inventory = data.has_scope_inventory
            if data.has_scope_orders is not None:
                user_scope.has_scope_orders = data.has_scope_orders
            if data.has_scope_customers is not None:
                user_scope.has_scope_customers = data.has_scope_customers
            if data.has_scope_reports is not None:
                user_scope.has_scope_reports = data.has_scope_reports
            if data.has_scope_analytics is not None:
                user_scope.has_scope_analytics = data.has_scope_analytics
            if data.has_scope_users is not None:
                user_scope.has_scope_users = data.has_scope_users
            
            user_scope.save()
            
            logger.info(f"Usuario '{user.username}' actualizado por {request.auth.username}")
            
            return serialize_user(user)
            
    except ValidationError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        logger.error(f"Error actualizando usuario {user_id}: {str(e)}")
        raise HttpError(500, "Error interno del servidor")

@users_router.delete("/{user_id}")
def delete_user(request, user_id: int):
    """Eliminar un usuario"""
    check_users_permission(request)
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        # No permitir eliminar superusuarios
        if user.is_superuser:
            raise HttpError(400, "No se puede eliminar un superusuario")
        
        # No permitir que un usuario se elimine a sí mismo
        if user.id == request.auth.id:
            raise HttpError(400, "No puedes eliminarte a ti mismo")
        
        username = user.username
        user.delete()
        
        logger.info(f"Usuario '{username}' eliminado por {request.auth.username}")
        
        return {"message": f"Usuario '{username}' eliminado exitosamente"}
        
    except Exception as e:
        logger.error(f"Error eliminando usuario {user_id}: {str(e)}")
        raise HttpError(500, "Error interno del servidor")

@users_router.get("/groups/", response=List[GroupSchema])
def list_groups(request):
    """Listar todos los grupos disponibles"""
    check_users_permission(request)
    
    groups = Group.objects.all().order_by('name')
    return [{'id': group.id, 'name': group.name} for group in groups]

@users_router.post("/{user_id}/toggle-active/")
def toggle_user_active(request, user_id: int):
    """Activar/desactivar un usuario"""
    check_users_permission(request)
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        # No permitir desactivar superusuarios
        if user.is_superuser:
            raise HttpError(400, "No se puede desactivar un superusuario")
        
        # No permitir que un usuario se desactive a sí mismo
        if user.id == request.auth.id:
            raise HttpError(400, "No puedes desactivarte a ti mismo")
        
        user.is_active = not user.is_active
        user.save()
        
        status = "activado" if user.is_active else "desactivado"
        logger.info(f"Usuario '{user.username}' {status} por {request.auth.username}")
        
        return {
            "message": f"Usuario '{user.username}' {status} exitosamente",
            "is_active": user.is_active
        }
        
    except Exception as e:
        logger.error(f"Error cambiando estado del usuario {user_id}: {str(e)}")
        raise HttpError(500, "Error interno del servidor")