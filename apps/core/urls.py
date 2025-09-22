from django.urls import path
from . import auth_api

app_name = 'core'

urlpatterns = [
    path('auth/login/', auth_api.login, name='login'),
    path('auth/refresh/', auth_api.refresh_token, name='refresh'),
    path('auth/logout/', auth_api.logout, name='logout'),
    path('auth/me/', auth_api.me, name='me'),
]