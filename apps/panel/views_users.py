from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .security import scope_required, has_scope

@login_required
@scope_required('users')
def users_list(request):
    """Lista todos los usuarios del sistema"""
    users = User.objects.all().select_related().prefetch_related('groups')
    groups = Group.objects.all()
    
    return render(request, 'panel/users_list.html', {
        'users': users,
        'groups': groups
    })

@login_required
@scope_required('users')
def user_create(request):
    """Crear nuevo usuario"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        groups = request.POST.getlist('groups')
        
        # Validaciones básicas
        if not username or not email or not password:
            messages.error(request, 'Todos los campos obligatorios deben ser completados')
            return render(request, 'panel/user_create.html', {
                'groups': Group.objects.all()
            })
        
        # Verificar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ya existe un usuario con ese nombre de usuario')
            return render(request, 'panel/user_create.html', {
                'groups': Group.objects.all()
            })
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con ese email')
            return render(request, 'panel/user_create.html', {
                'groups': Group.objects.all()
            })
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Asignar grupos
        if groups:
            user.groups.set(Group.objects.filter(id__in=groups))
        
        messages.success(request, f'Usuario {username} creado exitosamente')
        return redirect('panel:users_list')
    
    return render(request, 'panel/user_create.html', {
        'groups': Group.objects.all()
    })

@login_required
@scope_required('users')
def user_edit(request, user_id):
    """Editar usuario existente"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Cambiar contraseña si se proporciona
        new_password = request.POST.get('password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        
        # Actualizar grupos
        groups = request.POST.getlist('groups')
        user.groups.set(Group.objects.filter(id__in=groups))
        
        # Actualizar scopes
        if hasattr(user, 'scope'):
            user_scope = user.scope
        else:
            from .models import UserScope
            user_scope = UserScope.objects.create(user=user)
        
        user_scope.has_scope_users = request.POST.get('has_scope_users') == 'on'
        user_scope.has_scope_dashboard = request.POST.get('has_scope_dashboard') == 'on'
        user_scope.has_scope_inventory = request.POST.get('has_scope_inventory') == 'on'
        user_scope.has_scope_orders = request.POST.get('has_scope_orders') == 'on'
        user_scope.has_scope_customers = request.POST.get('has_scope_customers') == 'on'
        user_scope.has_scope_reports = request.POST.get('has_scope_reports') == 'on'
        user_scope.has_scope_analytics = request.POST.get('has_scope_analytics') == 'on'
        user_scope.save()
        
        messages.success(request, f'Usuario {user.username} actualizado exitosamente')
        return redirect('panel:users_list')
    
    # Asegurar que el usuario tenga UserScope
    if not hasattr(user, 'scope'):
        from .models import UserScope
        UserScope.objects.create(user=user)
    
    return render(request, 'panel/user_edit.html', {
        'user_obj': user,
        'groups': Group.objects.all(),
        'user_groups': user.groups.all(),
        'user_scope': user.scope
    })

@login_required
@scope_required('users')
def user_detail(request, user_id):
    """Ver detalles de un usuario"""
    user = get_object_or_404(User, id=user_id)
    
    # Asegurar que el usuario tenga UserScope
    if not hasattr(user, 'scope'):
        from .models import UserScope
        UserScope.objects.create(user=user)
    
    return render(request, 'panel/user_detail.html', {
        'user_obj': user,
        'user_scope': user.scope
    })

@login_required
@scope_required('users')
@require_http_methods(["POST"])
def user_toggle_active(request, user_id):
    """Activar/desactivar usuario"""
    user = get_object_or_404(User, id=user_id)
    
    # No permitir desactivar al propio usuario
    if user == request.user:
        return JsonResponse({
            'success': False,
            'message': 'No puedes desactivar tu propia cuenta'
        })
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'activado' if user.is_active else 'desactivado'
    messages.success(request, f'Usuario {user.username} {status} exitosamente')
    
    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'Usuario {status} exitosamente'
    })

@login_required
@scope_required('users')
def user_roles_api(request, user_id):
    """API para obtener roles de un usuario"""
    user = get_object_or_404(User, id=user_id)
    
    return JsonResponse({
        'user_id': user.id,
        'username': user.username,
        'groups': [{
            'id': group.id,
            'name': group.name
        } for group in user.groups.all()],
        'scopes': get_user_scopes(user)
    })