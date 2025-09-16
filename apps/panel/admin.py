from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import UserScope


class UserScopeInline(admin.StackedInline):
    model = UserScope
    can_delete = False
    verbose_name_plural = 'Scopes de Usuario'
    fields = (
        ('has_scope_dashboard', 'has_scope_users'),
        ('has_scope_inventory', 'has_scope_orders'),
        ('has_scope_customers', 'has_scope_reports'),
        ('has_scope_analytics',)
    )


@admin.register(UserScope)
class UserScopeAdmin(admin.ModelAdmin):
    list_display = ('user', 'scope_summary', 'created_at', 'updated_at')
    list_filter = (
        'has_scope_dashboard', 'has_scope_inventory', 'has_scope_orders',
        'has_scope_customers', 'has_scope_reports', 'has_scope_analytics',
        'has_scope_users', 'created_at'
    )
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    ordering = ('user__username',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Scopes Básicos', {
            'fields': ('has_scope_dashboard', 'has_scope_users')
        }),
        ('Scopes Operativos', {
            'fields': ('has_scope_inventory', 'has_scope_orders', 'has_scope_customers')
        }),
        ('Scopes Analíticos', {
            'fields': ('has_scope_reports', 'has_scope_analytics')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def scope_summary(self, obj):
        """Muestra un resumen visual de los scopes activos."""
        scopes = []
        scope_mapping = {
            'has_scope_dashboard': ('📊', 'Dashboard'),
            'has_scope_inventory': ('📦', 'Inventario'),
            'has_scope_orders': ('🛒', 'Pedidos'),
            'has_scope_customers': ('👥', 'Clientes'),
            'has_scope_reports': ('📈', 'Reportes'),
            'has_scope_analytics': ('📊', 'Analytics'),
            'has_scope_users': ('👤', 'Usuarios'),
        }
        
        for field, (icon, name) in scope_mapping.items():
            if getattr(obj, field):
                scopes.append(f'{icon} {name}')
        
        if not scopes:
            return format_html('<span style="color: red;">Sin scopes</span>')
        
        return format_html('<span style="color: green;">{}</span>', ' | '.join(scopes))
    
    scope_summary.short_description = 'Scopes Activos'


# Extender el admin de User para incluir UserScope inline
class UserAdmin(admin.ModelAdmin):
    inlines = (UserScopeInline,)


# Desregistrar el admin original de User y registrar el personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)