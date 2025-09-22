from django.contrib import admin
from .models import Product, Benefit


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'brand', 'unit', 'category', 'price', 'tax_rate', 'is_active', 'created_at']
    list_filter = ['is_active', 'brand', 'category', 'unit', 'created_at']
    search_fields = ['code', 'name', 'brand', 'category']
    list_editable = ['price', 'tax_rate', 'is_active']
    ordering = ['-created_at', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'brand', 'unit', 'category')
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
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'segment', 'value', 'active_from', 'active_to', 'is_active', 'created_at']
    list_filter = ['type', 'segment', 'is_active', 'active_from', 'active_to', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']
    ordering = ['-created_at', 'name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'active_from'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'type', 'segment')
        }),
        ('Configuración', {
            'fields': ('value', 'combo_spec')
        }),
        ('Período de Vigencia', {
            'fields': ('active_from', 'active_to')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
