from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'segment', 'email', 'phone', 'tax_id', 'tax_condition')
    list_filter = ('segment', 'tax_condition')
    search_fields = ('name', 'email', 'phone', 'tax_id')
    list_editable = ('segment',)
    ordering = ('name',)
    readonly_fields = ('id',)
    
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
    )
