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
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserScope)
class UserScopeAdmin(admin.ModelAdmin):
    list_display = ('user', 'scope_summary', 'scope_count', 'created_at', 'updated_at')
    list_filter = (
        'has_scope_dashboard', 'has_scope_inventory', 'has_scope_orders',
        'has_scope_customers', 'has_scope_reports', 'has_scope_analytics',
        'has_scope_users', 'created_at'
    )
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    ordering = ('user__username',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'scope_count')
    actions = ['grant_all_scopes', 'revoke_all_scopes', 'grant_admin_scopes']
    
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
        ('Resumen', {
            'fields': ('scope_count',)
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
    
    def scope_count(self, obj):
        """Cuenta el número de scopes activos."""
        count = sum([
            obj.has_scope_dashboard, obj.has_scope_inventory, obj.has_scope_orders,
            obj.has_scope_customers, obj.has_scope_reports, obj.has_scope_analytics,
            obj.has_scope_users
        ])
        return format_html('<span style="font-weight: bold; color: blue;">{}/7</span>', count)
    scope_count.short_description = 'Total Scopes'
    
    def grant_all_scopes(self, request, queryset):
        """Otorgar todos los scopes a usuarios seleccionados."""
        updated = queryset.update(
            has_scope_dashboard=True,
            has_scope_inventory=True,
            has_scope_orders=True,
            has_scope_customers=True,
            has_scope_reports=True,
            has_scope_analytics=True,
            has_scope_users=True
        )
        self.message_user(request, f'{updated} usuarios con todos los scopes otorgados.')
    grant_all_scopes.short_description = 'Otorgar todos los scopes'
    
    def revoke_all_scopes(self, request, queryset):
        """Revocar todos los scopes de usuarios seleccionados."""
        updated = queryset.update(
            has_scope_dashboard=False,
            has_scope_inventory=False,
            has_scope_orders=False,
            has_scope_customers=False,
            has_scope_reports=False,
            has_scope_analytics=False,
            has_scope_users=False
        )
        self.message_user(request, f'{updated} usuarios con todos los scopes revocados.')
    revoke_all_scopes.short_description = 'Revocar todos los scopes'
    
    def grant_admin_scopes(self, request, queryset):
        """Otorgar scopes de administrador."""
        updated = queryset.update(
            has_scope_dashboard=True,
            has_scope_users=True,
            has_scope_reports=True,
            has_scope_analytics=True
        )
        self.message_user(request, f'{updated} usuarios con scopes de admin otorgados.')
    grant_admin_scopes.short_description = 'Otorgar scopes de admin'


# Extender el admin de User para incluir UserScope inline
class UserAdmin(admin.ModelAdmin):
    inlines = (UserScopeInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)


# Desregistrar el admin original de User y registrar el personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)