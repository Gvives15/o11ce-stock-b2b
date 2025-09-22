from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.panel.models import Role, UserScope


class Command(BaseCommand):
    help = 'Asigna roles a usuarios basado en sus scopes existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué cambios se harían sin ejecutarlos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Mapeo de scopes a roles
        scope_to_role_mapping = {
            'admin': ['admin'],
            'vendedor_caja': ['vendedor_caja'],
            'vendedor_ruta': ['vendedor_ruta'],
        }
        
        # Obtener todos los usuarios con scopes
        users_with_scopes = User.objects.filter(scope__isnull=False).select_related('scope')
        
        if not users_with_scopes.exists():
            self.stdout.write(
                self.style.WARNING('No se encontraron usuarios con scopes asignados')
            )
            return

        # Obtener roles
        roles = {role.name: role for role in Role.objects.all()}
        
        if not roles:
            self.stdout.write(
                self.style.ERROR('No se encontraron roles. Ejecuta primero: python manage.py seed_roles')
            )
            return

        assigned_count = 0
        
        for user in users_with_scopes:
            scope = user.scope
            user_roles = []
            
            # Determinar roles basado en scopes
            if user.is_superuser:
                user_roles = ['admin']
            elif scope.has_scope_users:
                user_roles = ['admin']
            elif scope.has_scope_orders and scope.has_scope_customers and not scope.has_scope_inventory:
                # Si tiene pedidos y clientes pero no inventario, probablemente es vendedor
                if scope.has_scope_reports:
                    user_roles = ['vendedor_caja']  # vendedor_caja tiene reportes
                else:
                    user_roles = ['vendedor_ruta']  # vendedor_ruta no tiene reportes
            else:
                # Usuario básico sin roles específicos
                continue
            
            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Usuario "{user.username}" → Roles: {user_roles}'
                )
            else:
                # Asignar roles
                role_objects = [roles[role_name] for role_name in user_roles if role_name in roles]
                scope.roles.set(role_objects)
                assigned_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Usuario "{user.username}" → Roles: {user_roles}')
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\n[DRY RUN] Se asignarían roles a {assigned_count} usuarios')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 Roles asignados a {assigned_count} usuarios')
            )
