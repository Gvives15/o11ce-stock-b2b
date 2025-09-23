# Generated migration for pg_trgm extension

from django.db import migrations

try:
    from django.contrib.postgres.operations import TrigramExtension
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_benefit_idx_benefit_segment_active_and_more'),
    ]

    operations = []
    
    if POSTGRES_AVAILABLE:
        operations.append(
            TrigramExtension(),
        )
