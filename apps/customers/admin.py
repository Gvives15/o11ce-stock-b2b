from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'segment', 'email', 'phone', 'tax_id', 'tax_condition', 
        'orders_count'
    )
    list_filter = ('segment', 'tax_condition')
    search_fields = ('name', 'email', 'phone', 'tax_id')
    list_editable = ('segment',)
    ordering = ('name',)
    readonly_fields = ('id', 'orders_count')
    actions = ['upgrade_to_premium', 'downgrade_to_standard']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'segment')
        }),
        ('Contacto', {
            'fields': ('email', 'phone')
        }),
        ('Información Fiscal', {
            'fields': ('tax_id', 'tax_condition')
        }),
        ('Resumen', {
            'fields': ('orders_count',)
        }),
    )
    
    def segment_display(self, obj):
        """Muestra el segmento con colores."""
        colors = {
            'premium': 'gold',
            'standard': 'blue',
            'basic': 'gray'
        }
        color = colors.get(obj.segment, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_segment_display()
        )
    segment_display.short_description = 'Segmento'
    segment_display.admin_order_field = 'segment'
    
    def orders_count(self, obj):
        """Cuenta el número de pedidos del cliente."""
        count = obj.order_set.count()
        return format_html('<span style="color: blue;">{} pedidos</span>', count)
    orders_count.short_description = 'Pedidos'
    
    def upgrade_to_premium(self, request, queryset):
        """Actualizar clientes a premium."""
        updated = queryset.update(segment='premium')
        self.message_user(request, f'{updated} clientes actualizados a premium.')
    upgrade_to_premium.short_description = 'Actualizar a premium'
    
    def downgrade_to_standard(self, request, queryset):
        """Actualizar clientes a standard."""
        updated = queryset.update(segment='standard')
        self.message_user(request, f'{updated} clientes actualizados a standard.')
    downgrade_to_standard.short_description = 'Actualizar a standard'
    
    def get_queryset(self, request):
        """Optimizar consultas."""
        return super().get_queryset(request).annotate(
            orders_count=Count('order')
        )
