"""
Tests para verificar que los decoradores de permisos B0-BE-02 funcionan correctamente.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.panel.models import Role, UserScope
from apps.core.example_protected_endpoints import (
    admin_only_endpoint,
    vendedor_endpoint,
    vendedor_caja_required,
    vendedor_ruta_required,
    pos_operation_required,
    cancellation_required
)


class B0BE02PermissionsTestCase(TestCase):
    """Tests para decoradores de permisos B0-BE-02."""

    def setUp(self):
        self.client = Client()
        
        # Crear roles
        self.admin_role = Role.objects.create(name='admin', description='Administrador')
        self.vendedor_caja_role = Role.objects.create(name='vendedor_caja', description='Vendedor de Caja')
        self.vendedor_ruta_role = Role.objects.create(name='vendedor_ruta', description='Vendedor de Ruta')
        
        # Crear usuarios
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='testpass123'
        )
        self.vendedor_caja_user = User.objects.create_user(
            username='vendedor_caja_user',
            email='vendedor_caja@example.com',
            password='testpass123'
        )
        self.vendedor_ruta_user = User.objects.create_user(
            username='vendedor_ruta_user',
            email='vendedor_ruta@example.com',
            password='testpass123'
        )
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Asignar roles
        admin_scope, _ = UserScope.objects.get_or_create(user=self.admin_user)
        admin_scope.roles.add(self.admin_role)
        
        vendedor_caja_scope, _ = UserScope.objects.get_or_create(user=self.vendedor_caja_user)
        vendedor_caja_scope.roles.add(self.vendedor_caja_role)
        
        vendedor_ruta_scope, _ = UserScope.objects.get_or_create(user=self.vendedor_ruta_user)
        vendedor_ruta_scope.roles.add(self.vendedor_ruta_role)

    def get_auth_headers(self, username, password):
        """Obtiene headers de autenticación para un usuario."""
        login_response = self.client.post('/api/v1/auth/login/', {
            'username': username,
            'password': password
        }, content_type='application/json')
        
        if login_response.status_code == 200:
            data = login_response.json()
            return {'HTTP_AUTHORIZATION': f'Bearer {data["access"]}'}
        return {}

    def test_admin_can_access_admin_endpoint(self):
        """Test que admin puede acceder a endpoint de admin."""
        headers = self.get_auth_headers('admin_user', 'testpass123')
        response = self.client.get('/api/v1/admin-only/', **headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('admin', data['user_roles'])

    def test_vendedor_caja_cannot_access_admin_endpoint(self):
        """Test que vendedor_caja NO puede acceder a endpoint de admin."""
        headers = self.get_auth_headers('vendedor_caja_user', 'testpass123')
        response = self.client.get('/api/v1/admin-only/', **headers)
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['error'], 'INSUFFICIENT_PERMISSIONS')

    def test_vendedor_caja_can_access_vendedor_endpoint(self):
        """Test que vendedor_caja puede acceder a endpoint de vendedor."""
        headers = self.get_auth_headers('vendedor_caja_user', 'testpass123')
        response = self.client.get('/api/v1/vendedor/', **headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('vendedor_caja', data['user_roles'])

    def test_vendedor_ruta_can_access_vendedor_endpoint(self):
        """Test que vendedor_ruta puede acceder a endpoint de vendedor."""
        headers = self.get_auth_headers('vendedor_ruta_user', 'testpass123')
        response = self.client.get('/api/v1/vendedor/', **headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('vendedor_ruta', data['user_roles'])

    def test_regular_user_cannot_access_protected_endpoints(self):
        """Test que usuario regular NO puede acceder a endpoints protegidos."""
        headers = self.get_auth_headers('regular_user', 'testpass123')
        
        # Intentar acceder a endpoint de admin
        response = self.client.get('/api/v1/admin-only/', **headers)
        self.assertEqual(response.status_code, 403)
        
        # Intentar acceder a endpoint de vendedor
        response = self.client.get('/api/v1/vendedor/', **headers)
        self.assertEqual(response.status_code, 403)

    def test_unauthorized_access_returns_401(self):
        """Test que acceso sin token devuelve 401."""
        response = self.client.get('/api/v1/admin-only/')
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'MISSING_TOKEN')
