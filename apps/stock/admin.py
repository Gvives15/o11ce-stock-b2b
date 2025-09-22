from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Warehouse, StockLot, Movement


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'stock_summary')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)
    ordering = ('name',)
    readonly_fields = ('id', 'stock_summary')
    actions = ['activate_warehouses', 'deactivate_warehouses']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'is_active')
        }),
        ('Resumen', {
            'fields': ('stock_summary',)
        }),
    )
    
    def stock_summary(self, obj):
        """Muestra un resumen del stock en el almacén."""
        lots_count = StockLot.objects.filter(warehouse=obj).count()
        total_qty = sum(lot.qty_on_hand for lot in StockLot.objects.filter(warehouse=obj))
        return format_html(
            '<span style="color: blue;">{} lotes, {:.1f} unidades</span>', 
            lots_count, float(total_qty)
        )
    stock_summary.short_description = 'Resumen Stock'
    
    def activate_warehouses(self, request, queryset):
        """Activar almacenes seleccionados."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} almacenes activados.')
    activate_warehouses.short_description = 'Activar almacenes seleccionados'
    
    def deactivate_warehouses(self, request, queryset):
        """Desactivar almacenes seleccionados."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} almacenes desactivados.')
    deactivate_warehouses.short_description = 'Desactivar almacenes seleccionados'


@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'lot_code', 'qty_on_hand', 'qty_available_display', 'unit_cost', 
        'expiry_date', 'expiry_status', 'warehouse', 'status_flags', 'created_at'
    )
    list_filter = (
        'warehouse', 'is_quarantined', 'is_reserved', 'product__category', 
        'product__brand', 'expiry_date', 'created_at'
    )
    search_fields = ('product__code', 'product__name', 'lot_code')
    date_hierarchy = 'expiry_date'
    ordering = ('expiry_date', 'product__code')
    readonly_fields = ('id', 'created_at', 'qty_available', 'expiry_status')
    actions = ['quarantine_lots', 'unquarantine_lots', 'reserve_lots', 'unreserve_lots']
    list_per_page = 50
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('product', 'lot_code', 'warehouse')
        }),
        ('Inventario', {
            'fields': ('qty_on_hand', 'qty_available', 'unit_cost')
        }),
        ('Estado', {
            'fields': ('is_quarantined', 'is_reserved')
        }),
        ('Vencimiento', {
            'fields': ('expiry_date', 'expiry_status')
        }),
        ('Fechas', {
            'fields': ('created_at',)
        }),
    )
    
    def qty_available_display(self, obj):
        """Muestra la cantidad disponible con colores."""
        qty_available = obj.qty_available
        if qty_available == 0:
            return format_html('<span style="color: red; font-weight: bold;">0</span>')
        elif qty_available < obj.qty_on_hand:
            return format_html('<span style="color: orange;">{}</span>', qty_available)
        else:
            return format_html('<span style="color: green;">{}</span>', qty_available)
    
    qty_available_display.short_description = 'Qty Disponible'
    
    def status_flags(self, obj):
        """Muestra flags de estado del lote."""
        flags = []
        if obj.is_quarantined:
            flags.append('<span style="background: red; color: white; padding: 2px 4px; border-radius: 3px; font-size: 10px;">CUARENTENA</span>')
        if obj.is_reserved:
            flags.append('<span style="background: orange; color: white; padding: 2px 4px; border-radius: 3px; font-size: 10px;">RESERVADO</span>')
        if not flags:
            flags.append('<span style="color: green;">✓ Disponible</span>')
        return format_html(' '.join(flags))
    
    status_flags.short_description = 'Estado'
    
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
    list_filter = ('type', 'reason', 'product__category', 'product__brand', 'created_by', 'created_at')
    search_fields = ('product__code', 'product__name', 'lot__lot_code', 'order__id')
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
    
    def quarantine_lots(self, request, queryset):
        """Poner lotes en cuarentena."""
        updated = queryset.update(is_quarantined=True)
        self.message_user(request, f'{updated} lotes puestos en cuarentena.')
    quarantine_lots.short_description = 'Poner en cuarentena'
    
    def unquarantine_lots(self, request, queryset):
        """Quitar lotes de cuarentena."""
        updated = queryset.update(is_quarantined=False)
        self.message_user(request, f'{updated} lotes quitados de cuarentena.')
    unquarantine_lots.short_description = 'Quitar de cuarentena'
    
    def reserve_lots(self, request, queryset):
        """Reservar lotes."""
        updated = queryset.update(is_reserved=True)
        self.message_user(request, f'{updated} lotes reservados.')
    reserve_lots.short_description = 'Reservar lotes'
    
    def unreserve_lots(self, request, queryset):
        """Quitar reserva de lotes."""
        updated = queryset.update(is_reserved=False)
        self.message_user(request, f'{updated} lotes sin reserva.')
    unreserve_lots.short_description = 'Quitar reserva'
