"""
Configuration for mutmut mutation testing.
"""

def pre_mutation(context):
    """
    Pre-mutation hook to filter which mutations to apply.
    """
    # Skip mutations in test files
    if 'test_' in context.filename or '/tests/' in context.filename:
        return False
    
    # Skip mutations in migration files
    if '/migrations/' in context.filename:
        return False
    
    # Skip mutations in __init__.py files
    if context.filename.endswith('__init__.py'):
        return False
    
    # Skip mutations in settings files
    if 'settings' in context.filename:
        return False
    
    # Focus on catalog module for Block 4
    if 'apps/catalog/' not in context.filename:
        return False
    
    return True


def post_mutation(context):
    """
    Post-mutation hook for additional processing.
    """
    pass


# Mutmut configuration
MUTMUT_CONFIG = {
    # Target minimum mutation score
    'target_score': 60,
    
    # Paths to include in mutation testing
    'paths_to_mutate': [
        'apps/catalog/api.py',
        'apps/catalog/utils.py', 
        'apps/catalog/models.py',
        'apps/catalog/pricing.py'
    ],
    
    # Test command to run
    'test_command': 'python manage.py test apps.catalog.tests.api',
    
    # Timeout for each test run (seconds)
    'test_timeout': 60,
    
    # Number of parallel processes
    'processes': 4,
    
    # Skip equivalent mutants
    'skip_equivalent': True,
    
    # Output format
    'output_format': 'json'
}