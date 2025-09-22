from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('id', 'total_price')
    fields = ('product', 'qty', 'unit_price', 'benefit_applied', 'total_price')
    
    def total_price(self, obj):
        """Calcula el precio total del item."""
        if obj.qty and obj.unit_price:
            total_formatted = f"{float(obj.qty * obj.unit_price):.2f}"
            return format_html('<strong>${}</strong>', total_formatted)
        return '-'
    total_price.short_description = 'Total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'status_display', 'total_display', 'delivery_method', 
        'requested_delivery_date', 'items_count', 'created_at'
    )
    list_filter = ('status', 'delivery_method', 'currency', 'created_at', 'requested_delivery_date')
    search_fields = ('customer__name', 'client_req_id', 'delivery_address_text')
    list_editable = ()
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'client_req_id', 'items_count', 'total_display')
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']
    list_per_page = 50
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('customer', 'status', 'client_req_id')
        }),
        ('Montos', {
            'fields': ('currency', 'subtotal', 'discount_total', 'tax_total', 'total', 'total_display')
        }),
        ('Entrega', {
            'fields': ('delivery_method', 'delivery_address_text', 'requested_delivery_date', 
                      'delivery_window_from', 'delivery_window_to', 'delivery_instructions')
        }),
        ('Resumen', {
            'fields': ('items_count',)
        }),
        ('Fechas', {
            'fields': ('created_at',)
        }),
    )
    
    def status_display(self, obj):
        """Muestra el estado con colores."""
        status_colors = {
            'pending': 'orange',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red'
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Estado'
    status_display.admin_order_field = 'status'
    
    def total_display(self, obj):
        """Muestra el total con formato de moneda."""
        total_formatted = f"{float(obj.total):.2f}"
        return format_html('<strong>${}</strong>', total_formatted)
    total_display.short_description = 'Total'
    total_display.admin_order_field = 'total'
    
    def items_count(self, obj):
        """Cuenta el número de items en el pedido."""
        count = obj.orderitem_set.count()
        return format_html('<span style="color: blue;">{} items</span>', count)
    items_count.short_description = 'Items'
    
    def mark_as_processing(self, request, queryset):
        """Marcar pedidos como procesando."""
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} pedidos marcados como procesando.')
    mark_as_processing.short_description = 'Marcar como procesando'
    
    def mark_as_shipped(self, request, queryset):
        """Marcar pedidos como enviados."""
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} pedidos marcados como enviados.')
    mark_as_shipped.short_description = 'Marcar como enviados'
    
    def mark_as_delivered(self, request, queryset):
        """Marcar pedidos como entregados."""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} pedidos marcados como entregados.')
    mark_as_delivered.short_description = 'Marcar como entregados'
    
    def mark_as_cancelled(self, request, queryset):
        """Marcar pedidos como cancelados."""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} pedidos marcados como cancelados.')
    mark_as_cancelled.short_description = 'Marcar como cancelados'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'qty', 'unit_price', 'total_price', 'benefit_applied')
    list_filter = ('order__status', 'product__category', 'product__brand')
    search_fields = ('order__id', 'product__code', 'product__name')
    ordering = ('-order__created_at', 'product__code')
    readonly_fields = ('id', 'total_price')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('order', 'product')
        }),
        ('Cantidad y Precio', {
            'fields': ('qty', 'unit_price', 'total_price')
        }),
        ('Beneficios', {
            'fields': ('benefit_applied',)
        }),
    )
    
    def total_price(self, obj):
        """Calcula el precio total del item."""
        if obj.qty and obj.unit_price:
            total_formatted = f"{float(obj.qty * obj.unit_price):.2f}"
            return format_html('<strong>${}</strong>', total_formatted)
        return '-'
    total_price.short_description = 'Total'
