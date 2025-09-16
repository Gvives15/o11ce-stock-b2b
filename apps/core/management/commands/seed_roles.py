from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Crea los grupos base para el sistema RBAC'

    def handle(self, *args, **options):
        # Definir los grupos y sus descripciones
        groups_data = {
            'Admin': {
                'description': 'Acceso completo al sistema',
            },
            'Encargado_Inventario': {
                'description': 'Gestión de inventario, pedidos y reportes',
            },
            'Vendedor_Caja': {
                'description': 'Operaciones de venta en caja y atención al cliente',
            },
            'Vendedor_Ruta': {
                'description': 'Gestión de pedidos y clientes en ruta',
            }
        }

        created_groups = []
        
        for group_name, group_info in groups_data.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                created_groups.append(group_name)
                self.stdout.write(
                    self.style.SUCCESS(f'Grupo "{group_name}" creado exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Grupo "{group_name}" ya existe')
                )

        if created_groups:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSe crearon {len(created_groups)} grupos nuevos: {", ".join(created_groups)}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Todos los grupos ya existían en el sistema')
            )

        self.stdout.write(
            self.style.SUCCESS('\n=== Grupos disponibles ===')
        )
        for group in Group.objects.all().order_by('name'):
            self.stdout.write(f'- {group.name}')
            
        self.stdout.write(
            self.style.SUCCESS('\n=== Scopes por rol ===')
        )
        from apps.panel.security import SCOPES
        for role, scopes in SCOPES.items():
            self.stdout.write(f'- {role}: {", ".join(scopes)}')