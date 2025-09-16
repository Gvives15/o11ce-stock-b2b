from django.contrib import admin
from .models import Product, Benefit


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'brand', 'category', 'price', 'unit', 'is_active', 'low_stock_threshold')
    list_filter = ('is_active', 'category', 'brand', 'unit')
    search_fields = ('code', 'name', 'brand')
    list_editable = ('price', 'is_active', 'low_stock_threshold')
    ordering = ('code',)
    readonly_fields = ('id',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'brand', 'category', 'unit')
        }),
        ('Precios y Impuestos', {
            'fields': ('price', 'tax_rate')
        }),
        ('Inventario', {
            'fields': ('low_stock_threshold',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'segment', 'value', 'active_from', 'active_to', 'is_active')
    list_filter = ('type', 'segment', 'is_active', 'active_from', 'active_to')
    search_fields = ('name',)
    list_editable = ('is_active',)
    date_hierarchy = 'active_from'
    ordering = ('-active_from',)
    readonly_fields = ('id',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'type', 'segment')
        }),
        ('Configuración', {
            'fields': ('value', 'combo_spec')
        }),
        ('Vigencia', {
            'fields': ('active_from', 'active_to', 'is_active')
        }),
    )
