from django.contrib import admin
from django.utils.html import format_html
# from .models import BaseModel, CacheEntry, HealthCheck


# @admin.register(BaseModel)
class BaseModelAdmin(admin.ModelAdmin):
    """Admin para modelos base."""
    list_display = ('id', 'created_at', 'updated_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        """No permitir agregar modelos base directamente."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar modelos base."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar modelos base."""
        return False


# @admin.register(CacheEntry)
class CacheEntryAdmin(admin.ModelAdmin):
    """Admin para entradas de caché."""
    list_display = ('key', 'value_preview', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('created_at', 'expires_at')
    search_fields = ('key',)
    readonly_fields = ('key', 'value', 'created_at', 'expires_at', 'is_expired')
    ordering = ('-created_at',)
    
    def value_preview(self, obj):
        """Muestra una vista previa del valor."""
        value_str = str(obj.value)
        if len(value_str) > 50:
            return format_html('<span title="{}">{}...</span>', value_str, value_str[:50])
        return value_str
    value_preview.short_description = 'Valor'
    
    def is_expired(self, obj):
        """Indica si la entrada ha expirado."""
        from django.utils import timezone
        if obj.expires_at and obj.expires_at < timezone.now():
            return format_html('<span style="color: red;">✓ Expirado</span>')
        return format_html('<span style="color: green;">✓ Válido</span>')
    is_expired.short_description = 'Estado'
    is_expired.admin_order_field = 'expires_at'
    
    def has_add_permission(self, request):
        """No permitir agregar entradas de caché manualmente."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar entradas de caché."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminar entradas de caché."""
        return True


# @admin.register(HealthCheck)
class HealthCheckAdmin(admin.ModelAdmin):
    """Admin para verificaciones de salud."""
    list_display = ('service', 'status_display', 'response_time', 'checked_at', 'details_preview')
    list_filter = ('service', 'status', 'checked_at')
    search_fields = ('service', 'details')
    readonly_fields = ('service', 'status', 'response_time', 'checked_at', 'details')
    ordering = ('-checked_at',)
    
    def status_display(self, obj):
        """Muestra el estado con colores."""
        colors = {
            'healthy': 'green',
            'unhealthy': 'red',
            'warning': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Estado'
    status_display.admin_order_field = 'status'
    
    def details_preview(self, obj):
        """Muestra una vista previa de los detalles."""
        if obj.details:
            details_str = str(obj.details)
            if len(details_str) > 100:
                return format_html('<span title="{}">{}...</span>', details_str, details_str[:100])
            return details_str
        return '-'
    details_preview.short_description = 'Detalles'
    
    def has_add_permission(self, request):
        """No permitir agregar verificaciones de salud manualmente."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar verificaciones de salud."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminar verificaciones de salud."""
        return True
