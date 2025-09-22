"""Modelos para el panel administrativo."""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(models.Model):
    """Modelo para roles de usuario específicos del sistema."""
    
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('vendedor_caja', 'Vendedor de Caja'),
        ('vendedor_ruta', 'Vendedor de Ruta'),
    ]
    
    name = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        unique=True,
        verbose_name="Nombre del Rol"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['name']
    
    def __str__(self):
        return self.get_name_display()


class UserScope(models.Model):
    """Scopes/permisos específicos por usuario."""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='scope'
    )
    
    # Relación con roles específicos
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name='users',
        verbose_name="Roles del Usuario"
    )
    
    # Scopes disponibles
    has_scope_users = models.BooleanField(default=False, verbose_name="Gestión de Usuarios")
    has_scope_dashboard = models.BooleanField(default=True, verbose_name="Dashboard")
    has_scope_inventory = models.BooleanField(default=False, verbose_name="Inventario")
    has_scope_orders = models.BooleanField(default=False, verbose_name="Pedidos")
    has_scope_customers = models.BooleanField(default=False, verbose_name="Clientes")
    has_scope_reports = models.BooleanField(default=False, verbose_name="Reportes")
    has_scope_analytics = models.BooleanField(default=False, verbose_name="Analytics")
    has_scope_pos_override = models.BooleanField(default=False, verbose_name="Override POS")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Scope de Usuario"
        verbose_name_plural = "Scopes de Usuarios"
    
    def __str__(self):
        return f"Scopes de {self.user.username}"


@receiver(post_save, sender=User)
def create_user_scope(sender, instance, created, **kwargs):
    """Crear UserScope automáticamente al crear un usuario."""
    if created:
        UserScope.objects.create(
            user=instance,
            has_scope_dashboard=True  # Dashboard por defecto
        )


@receiver(post_save, sender=User)
def save_user_scope(sender, instance, **kwargs):
    """Guardar UserScope cuando se guarda el usuario."""
    if hasattr(instance, 'scope'):
        instance.scope.save()
    else:
        # Si no existe, crear uno
        UserScope.objects.create(
            user=instance,
            has_scope_dashboard=True
        )