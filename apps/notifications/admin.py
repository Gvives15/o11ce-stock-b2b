from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('event', 'channel', 'status_display', 'created_at', 'sent_at', 'payload_summary')
    list_filter = ('event', 'channel', 'sent_at', 'created_at')
    search_fields = ('event', 'payload')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('event', 'channel')
        }),
        ('Contenido', {
            'fields': ('payload',)
        }),
        ('Estado', {
            'fields': ('created_at', 'sent_at')
        }),
    )
    
    def status_display(self, obj):
        """Muestra el estado de la notificación con iconos."""
        if obj.sent_at:
            return format_html('<span style="color: green;">✓ Enviada</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pendiente</span>')
    
    status_display.short_description = 'Estado'
    
    def payload_summary(self, obj):
        """Muestra un resumen del payload."""
        if isinstance(obj.payload, dict):
            # Mostrar las primeras claves del payload
            keys = list(obj.payload.keys())[:3]
            if len(obj.payload) > 3:
                keys.append('...')
            return ', '.join(keys)
        return str(obj.payload)[:50] + ('...' if len(str(obj.payload)) > 50 else '')
    
    payload_summary.short_description = 'Resumen Payload'
    
    actions = ['mark_as_sent']
    
    def mark_as_sent(self, request, queryset):
        """Acción para marcar notificaciones como enviadas."""
        updated = queryset.filter(sent_at__isnull=True).update(sent_at=timezone.now())
        self.message_user(request, f'{updated} notificaciones marcadas como enviadas.')
    
    mark_as_sent.short_description = 'Marcar como enviadas'
