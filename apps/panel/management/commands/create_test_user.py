from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.panel.models import Role, UserScope

User = get_user_model()

# Matriz de roles y scopes basada en la lógica del negocio
ROLE_SCOPE_MATRIX = {
    'admin': {
        'has_scope_users': True,
        'has_scope_dashboard': True,
        'has_scope_inventory_level_1': True,
        'has_scope_inventory_level_2': True,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_catalog': True,
        'has_scope_caja': True,
        'has_scope_reports': True,
        'has_scope_analytics': True,
    },
    'encargado': {
        'has_scope_users': True,
        'has_scope_dashboard': True,
        'has_scope_inventory_level_1': True,
        'has_scope_inventory_level_2': True,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_catalog': True,
        'has_scope_caja': True,
        'has_scope_reports': False,
        'has_scope_analytics': False,
    },
    'vendedor_caja': {
        'has_scope_users': False,
        'has_scope_dashboard': True,
        'has_scope_inventory_level_1': True,
        'has_scope_inventory_level_2': False,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_catalog': False,
        'has_scope_caja': True,
        'has_scope_reports': False,
        'has_scope_analytics': False,
    },
    'vendedor_ruta': {
        'has_scope_users': False,
        'has_scope_dashboard': True,
        'has_scope_inventory_level_1': True,
        'has_scope_inventory_level_2': False,
        'has_scope_orders': True,
        'has_scope_customers': True,
        'has_scope_catalog': False,
        'has_scope_caja': False,
        'has_scope_reports': False,
        'has_scope_analytics': False,
    }
}


class Command(BaseCommand):
    help = 'Crea el usuario de prueba Alejandro Vives con rol encargado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='alejandro.vives',
            help='Username para el usuario de prueba'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='ale12345',
            help='Password para el usuario de prueba'
        )
        parser.add_argument(
            '--role',
            type=str,
            default='encargado',
            help='Rol para el usuario de prueba'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        role_name = options['role']

        # Datos del usuario
        user_data = {
            'username': username,
            'email': f'{username}@example.com',
            'first_name': 'Alejandro',
            'last_name': 'Vives',
            'is_active': True,
            'is_staff': True,
        }

        try:
            # Verificar si el rol existe
            try:
                role = Role.objects.get(name=role_name)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ El rol "{role_name}" no existe. Ejecuta primero: python manage.py seed_roles')
                )
                return

            # Crear o actualizar usuario
            user, created = User.objects.get_or_create(
                username=username,
                defaults=user_data
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Usuario "{username}" creado exitosamente')
                )
            else:
                # Actualizar datos si el usuario ya existe
                for key, value in user_data.items():
                    if key != 'username':
                        setattr(user, key, value)
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.WARNING(f'↻ Usuario "{username}" actualizado')
                )

            # Crear o actualizar UserScope
            user_scope, scope_created = UserScope.objects.get_or_create(
                user=user,
                defaults={'role': role}
            )

            if not scope_created:
                user_scope.role = role

            # Aplicar scopes según el rol
            if role_name in ROLE_SCOPE_MATRIX:
                scopes = ROLE_SCOPE_MATRIX[role_name]
                for scope_field, has_access in scopes.items():
                    setattr(user_scope, scope_field, has_access)
                
                user_scope.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Scopes aplicados para rol "{role.get_name_display()}"')
                )
                
                # Mostrar scopes activos
                active_scopes = [field.replace('has_scope_', '') for field, value in scopes.items() if value]
                self.stdout.write(
                    self.style.SUCCESS(f'📋 Scopes activos: {", ".join(active_scopes)}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  No se encontraron scopes definidos para el rol "{role_name}"')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Usuario de prueba configurado:\n'
                    f'   👤 Usuario: {username}\n'
                    f'   🔑 Contraseña: {password}\n'
                    f'   👔 Rol: {role.get_name_display()}\n'
                    f'   📧 Email: {user.email}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al crear usuario: {str(e)}')
            )