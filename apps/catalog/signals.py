"""
Signals for cache invalidation on model changes.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product, Benefit
from apps.core.cache_service import CacheService


@receiver(post_save, sender=Product)
def invalidate_product_cache_on_save(sender, instance, **kwargs):
    """Invalidar cache de productos cuando se crea o actualiza un producto."""
    CacheService.invalidate_pattern("catalog_products")


@receiver(post_delete, sender=Product)
def invalidate_product_cache_on_delete(sender, instance, **kwargs):
    """Invalidar cache de productos cuando se elimina un producto."""
    CacheService.invalidate_pattern("catalog_products")


@receiver(post_save, sender=Benefit)
def invalidate_benefit_cache_on_save(sender, instance, **kwargs):
    """Invalidar cache relacionado con beneficios cuando se crea o actualiza un beneficio."""
    # Invalidar cache de ofertas ya que los beneficios afectan las ofertas
    CacheService.invalidate_pattern("offers")
    CacheService.invalidate_pattern("catalog_products")  # Los productos pueden mostrar beneficios


@receiver(post_delete, sender=Benefit)
def invalidate_benefit_cache_on_delete(sender, instance, **kwargs):
    """Invalidar cache relacionado con beneficios cuando se elimina un beneficio."""
    # Invalidar cache de ofertas ya que los beneficios afectan las ofertas
    CacheService.invalidate_pattern("offers")
    CacheService.invalidate_pattern("catalog_products")  # Los productos pueden mostrar beneficios