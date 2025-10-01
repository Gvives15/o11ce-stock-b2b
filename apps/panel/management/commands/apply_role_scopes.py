from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from apps.panel.models import UserScope


class Command(BaseCommand):
    help = 'Aplica una matriz de scopes por rol a todos los usuarios'
    
    # Matriz de scopes por rol
    ROLE_SCOPES = {
        'admin': {
            'has_scope_dashboard': True,
            'has_scope_inventory': True,
            'has_scope_orders': True,
            'has_scope_customers': True,
            'has_scope_reports': True,
            'has_scope_analytics': True,
            'has_scope_users': True,
        },
        'encargado': {
            'has_scope_dashboard': True,
            'has_scope_inventory': True,
            'has_scope_orders': True,
            'has_scope_customers': True,
            'has_scope_reports': True,
            'has_scope_analytics': False,
            'has_scope_users': False,
        },
        'manager': {
            'has_scope_dashboard': True,
            'has_scope_inventory': True,
            'has_scope_orders': True,
            'has_scope_customers': True,
            'has_scope_reports': True,
            'has_scope_analytics': True,
            'has_scope_users': False,
        },
        'employee': {
            'has_scope_dashboard': True,
            'has_scope_inventory': True,
            'has_scope_orders': True,
            'has_scope_customers': True,
            'has_scope_reports': False,
            'has_scope_analytics': False,
            'has_scope_users': False,
        },
        'viewer': {
            'has_scope_dashboard': True,
            'has_scope_inventory': False,
            'has_scope_orders': False,
            'has_scope_customers': False,
            'has_scope_reports': False,
            'has_scope_analytics': False,
            'has_scope_users': False,
        },
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='Aplicar scopes solo a usuarios de un rol específico',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué cambios se harían sin aplicarlos',
        )
        parser.add_argument(
            '--create-groups',
            action='store_true',
            help='Crear grupos que no existan',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_role = options['role']
        create_groups = options['create_groups']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se aplicarán cambios'))
        
        # Crear grupos si se solicita
        if create_groups:
            self.create_missing_groups(dry_run)
        
        # Obtener roles a procesar
        roles_to_process = [target_role] if target_role else self.ROLE_SCOPES.keys()
        
        total_updated = 0
        
        for role_name in roles_to_process:
            if role_name not in self.ROLE_SCOPES:
                self.stdout.write(
                    self.style.ERROR(f'Rol "{role_name}" no está definido en la matriz de scopes')
                )
                continue
            
            updated_count = self.apply_role_scopes(role_name, dry_run)
            total_updated += updated_count
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Se actualizarían {total_updated} usuarios en total')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Se actualizaron {total_updated} usuarios exitosamente')
            )
    
    def create_missing_groups(self, dry_run):
        """Crear grupos que no existan"""
        for role_name in self.ROLE_SCOPES.keys():
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                if dry_run:
                    self.stdout.write(f'Se crearía el grupo: {role_name}')
                else:
                    self.stdout.write(f'Grupo creado: {role_name}')
    
    def apply_role_scopes(self, role_name, dry_run):
        """Aplicar scopes a usuarios de un rol específico"""
        try:
            group = Group.objects.get(name=role_name)
        except Group.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'El grupo "{role_name}" no existe. Use --create-groups para crearlo.')
            )
            return 0
        
        users = User.objects.filter(groups=group, is_active=True)
        scopes_config = self.ROLE_SCOPES[role_name]
        
        self.stdout.write(f'\nProcesando rol: {role_name}')
        self.stdout.write(f'Usuarios encontrados: {users.count()}')
        
        updated_count = 0
        
        for user in users:
            # Asegurar que el usuario tenga UserScope
            user_scope, created = UserScope.objects.get_or_create(user=user)
            
            if created:
                self.stdout.write(f'  UserScope creado para: {user.username}')
            
            # Aplicar scopes según el rol
            changes_made = False
            changes_log = []
            
            for scope_field, should_have in scopes_config.items():
                current_value = getattr(user_scope, scope_field)
                if current_value != should_have:
                    changes_made = True
                    changes_log.append(f'{scope_field}: {current_value} -> {should_have}')
                    if not dry_run:
                        setattr(user_scope, scope_field, should_have)
            
            if changes_made:
                if dry_run:
                    self.stdout.write(f'  {user.username}: {", ".join(changes_log)}')
                else:
                    user_scope.save()
                    self.stdout.write(f'  Actualizado {user.username}: {", ".join(changes_log)}')
                updated_count += 1
            else:
                self.stdout.write(f'  {user.username}: Sin cambios necesarios')
        
        return updated_count
    
    def show_role_matrix(self):
        """Mostrar la matriz de scopes por rol"""
        self.stdout.write('\nMatriz de Scopes por Rol:')
        self.stdout.write('=' * 50)
        
        # Encabezados
        scopes = list(next(iter(self.ROLE_SCOPES.values())).keys())
        header = 'Rol'.ljust(12)
        for scope in scopes:
            header += scope.replace('has_scope_', '').ljust(12)
        self.stdout.write(header)
        self.stdout.write('-' * len(header))
        
        # Filas de datos
        for role, scopes_config in self.ROLE_SCOPES.items():
            row = role.ljust(12)
            for scope_field in scopes:
                value = 'Sí' if scopes_config[scope_field] else 'No'
                row += value.ljust(12)
            self.stdout.write(row)