from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    
    def ready(self):
        """Importar signals cuando la app esté lista."""
        import apps.catalog.signals
