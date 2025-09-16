from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('id',)
    fields = ('product', 'qty', 'unit_price', 'benefit_applied')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'total', 'delivery_method', 'requested_delivery_date', 'created_at')
    list_filter = ('status', 'delivery_method', 'currency', 'created_at', 'requested_delivery_date')
    search_fields = ('customer__name', 'client_req_id', 'delivery_address_text')
    list_editable = ('status',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'client_req_id')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('customer', 'status', 'client_req_id')
        }),
        ('Montos', {
            'fields': ('currency', 'subtotal', 'discount_total', 'tax_total', 'total')
        }),
        ('Entrega', {
            'fields': ('delivery_method', 'delivery_address_text', 'requested_delivery_date', 
                      'delivery_window_from', 'delivery_window_to', 'delivery_instructions')
        }),
        ('Fechas', {
            'fields': ('created_at',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'qty', 'unit_price', 'benefit_applied')
    list_filter = ('order__status', 'product__category', 'product__brand')
    search_fields = ('order__id', 'product__code', 'product__name')
    ordering = ('-order__created_at', 'product__code')
    readonly_fields = ('id',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('order', 'product')
        }),
        ('Cantidad y Precio', {
            'fields': ('qty', 'unit_price')
        }),
        ('Beneficios', {
            'fields': ('benefit_applied',)
        }),
    )
