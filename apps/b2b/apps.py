"""B2B BFF app configuration."""

from django.apps import AppConfig


class B2bConfig(AppConfig):
    """Configuration for B2B BFF app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.b2b'
    verbose_name = 'B2B Backend For Frontend'