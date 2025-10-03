"""Global pytest configuration for the BFF project."""

import os
import django
from django.conf import settings

# Configure Django settings for pytest
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')

# Setup Django
django.setup()