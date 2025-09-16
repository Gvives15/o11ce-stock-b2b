from django.contrib import admin
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
        'reason_short'
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
        'timestamp'
    ]
    
    ordering = ['-timestamp']
    
    date_hierarchy = 'timestamp'
    
    def sale_id_short(self, obj):
        """Muestra solo los primeros 8 caracteres del sale_id"""
        return obj.sale_id[:8] + '...' if len(obj.sale_id) > 8 else obj.sale_id
    sale_id_short.short_description = 'Sale ID'
    
    def reason_short(self, obj):
        """Muestra solo los primeros 50 caracteres de la razón"""
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_short.short_description = 'Reason'
    
    def has_add_permission(self, request):
        """No permitir agregar registros manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar registros"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar registros"""
        return False
