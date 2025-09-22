from django.urls import path
from . import auth_api, health

app_name = 'core'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', auth_api.login, name='login'),
    path('auth/refresh/', auth_api.refresh_token, name='refresh'),
    path('auth/logout/', auth_api.logout, name='logout'),
    path('auth/me/', auth_api.me, name='me'),
    
    # Health check endpoints
    path('health/live/', health.health_live, name='health_live'),
    path('health/ready/', health.health_ready, name='health_ready'),
]