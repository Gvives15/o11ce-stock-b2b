from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Warehouse, StockLot, Movement


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)
    ordering = ('name',)
    readonly_fields = ('id',)


@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ('product', 'lot_code', 'qty_on_hand', 'unit_cost', 'expiry_date', 'expiry_status', 'warehouse', 'created_at')
    list_filter = ('warehouse', 'product__category', 'product__brand', 'expiry_date', 'created_at')
    search_fields = ('product__code', 'product__name', 'lot_code')
    date_hierarchy = 'expiry_date'
    ordering = ('expiry_date', 'product__code')
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('product', 'lot_code', 'warehouse')
        }),
        ('Inventario', {
            'fields': ('qty_on_hand', 'unit_cost')
        }),
        ('Vencimiento', {
            'fields': ('expiry_date',)
        }),
        ('Fechas', {
            'fields': ('created_at',)
        }),
    )
    
    def expiry_status(self, obj):
        """Muestra el estado de vencimiento con colores."""
        today = timezone.now().date()
        days_to_expiry = (obj.expiry_date - today).days
        
        if days_to_expiry < 0:
            return format_html('<span style="color: red; font-weight: bold;">Vencido ({} días)</span>', abs(days_to_expiry))
        elif days_to_expiry <= 30:
            return format_html('<span style="color: orange; font-weight: bold;">Próximo a vencer ({} días)</span>', days_to_expiry)
        else:
            return format_html('<span style="color: green;">OK ({} días)</span>', days_to_expiry)
    
    expiry_status.short_description = 'Estado Vencimiento'


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ('type', 'product', 'lot', 'qty', 'unit_cost', 'reason', 'order', 'created_by', 'created_at')
    list_filter = ('type', 'product__category', 'product__brand', 'created_by', 'created_at')
    search_fields = ('product__code', 'product__name', 'lot__lot_code', 'reason', 'order__id')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('type', 'product', 'lot')
        }),
        ('Cantidad y Costo', {
            'fields': ('qty', 'unit_cost')
        }),
        ('Detalles', {
            'fields': ('reason', 'order')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimizar consultas con select_related."""
        return super().get_queryset(request).select_related(
            'product', 'lot', 'order', 'created_by'
        )
