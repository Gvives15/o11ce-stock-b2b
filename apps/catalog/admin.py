from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import Product, Benefit


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'brand', 'unit', 'pack_size_display', 'category', 
        'price_display', 'tax_rate', 'stock_status', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'brand', 'category', 'unit', 'created_at']
    search_fields = ['code', 'name', 'brand', 'category']
    list_editable = ['is_active']
    ordering = ['-created_at', 'name']
    readonly_fields = ['created_at', 'updated_at', 'stock_status']
    list_per_page = 25
    actions = ['activate_products', 'deactivate_products', 'update_tax_rates']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'brand', 'unit', 'category')
        }),
        ('Unidades y Paquetes', {
            'fields': ('pack_size',),
            'description': 'Configuración de equivalencias entre unidades y paquetes'
        }),
        ('Precios y Impuestos', {
            'fields': ('price', 'tax_rate')
        }),
        ('Inventario', {
            'fields': ('low_stock_threshold', 'stock_status')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def pack_size_display(self, obj):
        """Muestra el pack_size con formato mejorado."""
        if obj.pack_size and obj.pack_size > 1:
            return format_html('<span style="color: blue; font-weight: bold;">{}x</span>', obj.pack_size)
        return '-'
    pack_size_display.short_description = 'Pack Size'
    pack_size_display.admin_order_field = 'pack_size'
    
    def price_display(self, obj):
        """Muestra el precio con formato de moneda."""
        price_formatted = f"{float(obj.price):.2f}"
        return format_html('<span style="font-weight: bold;">${}</span>', price_formatted)
    price_display.short_description = 'Precio'
    price_display.admin_order_field = 'price'
    
    def stock_status(self, obj):
        """Muestra el estado del stock basado en el threshold."""
        if obj.low_stock_threshold:
            # Aquí podrías agregar lógica para calcular stock real
            return format_html('<span style="color: green;">✓ Configurado</span>')
        return format_html('<span style="color: orange;">⚠ Sin threshold</span>')
    stock_status.short_description = 'Estado Stock'
    
    def get_queryset(self, request):
        """Optimizar consultas."""
        return super().get_queryset(request)
    
    def activate_products(self, request, queryset):
        """Activar productos seleccionados."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} productos activados.')
    activate_products.short_description = 'Activar productos seleccionados'
    
    def deactivate_products(self, request, queryset):
        """Desactivar productos seleccionados."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} productos desactivados.')
    deactivate_products.short_description = 'Desactivar productos seleccionados'
    
    def update_tax_rates(self, request, queryset):
        """Actualizar tasas de impuesto a 21%."""
        updated = queryset.update(tax_rate=21)
        self.message_user(request, f'{updated} productos actualizados con tasa 21 porciento.')
    update_tax_rates.short_description = 'Actualizar tasas a 21 porciento'


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'type', 'segment', 'value_display', 'active_from', 'active_to', 
        'status_display', 'is_active', 'created_at'
    ]
    list_filter = ['type', 'segment', 'is_active', 'active_from', 'active_to', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']
    ordering = ['-created_at', 'name']
    readonly_fields = ['created_at', 'updated_at', 'status_display']
    date_hierarchy = 'active_from'
    actions = ['activate_benefits', 'deactivate_benefits']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'type', 'segment')
        }),
        ('Configuración', {
            'fields': ('value', 'combo_spec')
        }),
        ('Período de Vigencia', {
            'fields': ('active_from', 'active_to', 'status_display')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def value_display(self, obj):
        """Muestra el valor con formato apropiado."""
        if obj.value:
            if obj.type == 'discount':
                return format_html('<span style="color: green;">{} porciento</span>', obj.value)
            else:
                return format_html('<span style="color: blue;">{}</span>', obj.value)
        return '-'
    value_display.short_description = 'Valor'
    value_display.admin_order_field = 'value'
    
    def status_display(self, obj):
        """Muestra el estado de vigencia del beneficio."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if obj.active_from > today:
            return format_html('<span style="color: blue;">⏳ Futuro</span>')
        elif obj.active_to < today:
            return format_html('<span style="color: red;">❌ Vencido</span>')
        else:
            return format_html('<span style="color: green;">✅ Activo</span>')
    status_display.short_description = 'Estado Vigencia'
    
    def activate_benefits(self, request, queryset):
        """Activar beneficios seleccionados."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} beneficios activados.')
    activate_benefits.short_description = 'Activar beneficios seleccionados'
    
    def deactivate_benefits(self, request, queryset):
        """Desactivar beneficios seleccionados."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} beneficios desactivados.')
    deactivate_benefits.short_description = 'Desactivar beneficios seleccionados'
