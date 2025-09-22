from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import LotOverrideAudit


@admin.register(LotOverrideAudit)
class LotOverrideAuditAdmin(admin.ModelAdmin):
    """
    Interfaz de administración para auditoría de overrides de lotes.
    Permite consulta simple de todos los registros de override.
    """
    list_display = [
        'timestamp',
        'actor',
        'sale_id_short',
        'product',
        'lot_chosen',
        'qty',
        'reason_short',
        'time_ago'
    ]
    
    list_filter = [
        'timestamp',
        'actor',
        'product',
        'lot_chosen__product'
    ]
    
    search_fields = [
        'sale_id',
        'actor__username',
        'actor__first_name',
        'actor__last_name',
        'product__name',
        'product__code',
        'lot_chosen__lot_code',
        'reason'
    ]
    
    readonly_fields = [
        'actor',
        'sale_id',
        'product',
        'lot_chosen',
        'qty',
        'reason',
        'timestamp',
        'time_ago'
    ]
    
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 100
    
    fieldsets = (
        ('Información de la Venta', {
            'fields': ('sale_id', 'timestamp', 'time_ago')
        }),
        ('Actor', {
            'fields': ('actor',)
        }),
        ('Producto y Lote', {
            'fields': ('product', 'lot_chosen', 'qty')
        }),
        ('Razón', {
            'fields': ('reason',)
        }),
    )
    
    def sale_id_short(self, obj):
        """Muestra solo los primeros 8 caracteres del sale_id"""
        return format_html(
            '<span style="font-family: monospace; background: #f0f0f0; padding: 2px 4px; border-radius: 3px;">{}</span>',
            obj.sale_id[:8] + '...' if len(obj.sale_id) > 8 else obj.sale_id
        )
    sale_id_short.short_description = 'Sale ID'
    sale_id_short.admin_order_field = 'sale_id'
    
    def reason_short(self, obj):
        """Muestra solo los primeros 50 caracteres de la razón"""
        reason = obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
        return format_html('<span title="{}">{}</span>', obj.reason, reason)
    reason_short.short_description = 'Reason'
    
    def time_ago(self, obj):
        """Muestra el tiempo transcurrido desde el override."""
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days > 0:
            return format_html('<span style="color: #666;">{} días atrás</span>', diff.days)
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return format_html('<span style="color: #666;">{}h atrás</span>', hours)
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return format_html('<span style="color: #666;">{}m atrás</span>', minutes)
        else:
            return format_html('<span style="color: green;">Ahora</span>')
    time_ago.short_description = 'Hace'
    time_ago.admin_order_field = 'timestamp'
    
    def get_queryset(self, request):
        """Optimizar consultas."""
        return super().get_queryset(request).select_related(
            'actor', 'product', 'lot_chosen'
        )
    
    def has_add_permission(self, request):
        """No permitir agregar registros manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar registros"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar registros"""
        return False
