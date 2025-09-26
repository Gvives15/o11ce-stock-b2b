from django.contrib.auth.models import User
from apps.panel.models import UserScope

print('=== VERIFICACIÓN DE SCOPES POR USUARIO ===')
print()

for us in UserScope.objects.select_related('user').all():
    print(f'Usuario: {us.user.username}')
    print(f'  Dashboard: {us.has_scope_dashboard}')
    print(f'  Inventario: {us.has_scope_inventory}')
    print(f'  Pedidos: {us.has_scope_orders}')
    print(f'  Clientes: {us.has_scope_customers}')
    print(f'  Reportes: {us.has_scope_reports}')
    print(f'  Analytics: {us.has_scope_analytics}')
    print(f'  Usuarios: {us.has_scope_users}')
    print()

print('=== VERIFICACIÓN COMPLETADA ===')