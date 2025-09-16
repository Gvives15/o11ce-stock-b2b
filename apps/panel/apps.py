"""Configuración de la app Panel."""

from django.apps import AppConfig


class PanelConfig(AppConfig):
    """Configuración de la aplicación Panel."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.panel'
    verbose_name = 'Panel Administrativo'
    
    def ready(self):
        """Importar signals cuando la app esté lista."""
        import apps.panel.models  # noqa