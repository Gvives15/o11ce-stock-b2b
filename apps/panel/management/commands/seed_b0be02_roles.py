from django.core.management.base import BaseCommand
from apps.panel.models import Role


class Command(BaseCommand):
    help = 'Crea los roles básicos del sistema: admin, vendedor_caja, vendedor_ruta'

    def handle(self, *args, **options):
        roles_data = [
            {
                'name': 'admin',
                'description': 'Administrador del sistema con acceso completo a todas las funcionalidades'
            },
            {
                'name': 'vendedor_caja',
                'description': 'Vendedor de caja con acceso a ventas, clientes y reportes básicos'
            },
            {
                'name': 'vendedor_ruta',
                'description': 'Vendedor de ruta con acceso a ventas, clientes y gestión de pedidos'
            }
        ]

        created_count = 0
        updated_count = 0

        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                defaults={
                    'description': role_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Rol "{role.get_name_display()}" creado')
                )
            else:
                # Actualizar descripción si existe
                if role.description != role_data['description']:
                    role.description = role_data['description']
                    role.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Rol "{role.get_name_display()}" actualizado')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Rol "{role.get_name_display()}" ya existe')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Proceso completado: {created_count} roles creados, {updated_count} actualizados'
            )
        )
