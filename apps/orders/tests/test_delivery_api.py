"""
Tests para el endpoint de entrega atómica de órdenes.
Cubre casos felices, fallos intermedios con rollback, y errores 409.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ninja.testing import TestClient
from unittest.mock import patch

from apps.orders.models import Order, OrderItem
from apps.orders.picking_api import picking_router
from apps.orders.audit import DeliveryAuditLog, DeliveryAuditLogItem
from apps.stock.models import Product, Warehouse, StockLot, Movement
from apps.stock.reservations import Reservation
from apps.customers.models import Customer

User = get_user_model()


class DeliveryAPITestCase(TestCase):
    """Test case base para pruebas de entrega."""
    
    def setUp(self):
        """Configuración inicial para las pruebas."""
        self.client = TestClient(picking_router)
        
        # Crear usuario real para autenticación
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Crear warehouse
        self.warehouse = Warehouse.objects.create(
            name='Almacén Principal'
        )
        
        # Crear productos
        self.product1 = Product.objects.create(
            name='Producto A',
            code='PROD-A-001',
            price=Decimal('10.00')
        )
        
        self.product2 = Product.objects.create(
            name='Producto B',
            code='PROD-B-001',
            price=Decimal('15.00')
        )
        
        # Crear lotes con stock
        self.lot1 = StockLot.objects.create(
            product=self.product1,
            lot_code='LOT-A-001',
            expiry_date='2024-12-31',
            qty_on_hand=Decimal('100'),
            unit_cost=Decimal('10.00'),
            warehouse=self.warehouse
        )
        
        self.lot2 = StockLot.objects.create(
            product=self.product2,
            lot_code='LOT-B-001',
            expiry_date='2024-11-30',
            qty_on_hand=Decimal('50'),
            unit_cost=Decimal('15.00'),
            warehouse=self.warehouse
        )
        
        # Crear orden
        customer = Customer.objects.create(
            name='Cliente Test',
            segment=Customer.Segment.RETAIL
        )
        
        self.order = Order.objects.create(
            customer=customer,
            status=Order.Status.DRAFT
        )
        
        # Crear items de orden
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            qty=Decimal('20'),
            unit_price=Decimal('10.00')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            qty=Decimal('10'),
            unit_price=Decimal('15.00')
        )


class DeliveryHappyPathTestCase(DeliveryAPITestCase):
    """Pruebas para el caso feliz de entrega."""
    
    def test_deliver_order_success_multiple_movements(self):
        """Test: Entrega exitosa con múltiples movimientos."""
        # Crear reservas activas
        reservation1 = Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('20'),
            status=Reservation.Status.PENDING
        )
        
        reservation2 = Reservation.objects.create(
            order=self.order,
            lot=self.lot2,
            qty=Decimal('10'),
            status=Reservation.Status.PENDING
        )
        
        # Ejecutar entrega con usuario autenticado
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        # Verificar respuesta exitosa
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['order_id'], self.order.id)
        self.assertEqual(data['total_movements'], 2)
        self.assertEqual(len(data['movements']), 2)
        self.assertIn('audit_log_id', data)
        
        # Verificar movimientos creados
        movements = data['movements']
        
        # Movimiento 1
        mov1 = movements[0]
        self.assertEqual(mov1['lot_id'], self.lot1.id)
        self.assertEqual(mov1['lot_code'], 'LOT-A-001')
        self.assertEqual(Decimal(str(mov1['qty_delivered'])), Decimal('20'))
        self.assertEqual(Decimal(str(mov1['unit_cost'])), Decimal('10.00'))
        
        # Movimiento 2
        mov2 = movements[1]
        self.assertEqual(mov2['lot_id'], self.lot2.id)
        self.assertEqual(mov2['lot_code'], 'LOT-B-001')
        self.assertEqual(Decimal(str(mov2['qty_delivered'])), Decimal('10'))
        self.assertEqual(Decimal(str(mov2['unit_cost'])), Decimal('15.00'))
        
        # Verificar que se crearon los movimientos EXIT en BD
        exit_movements = Movement.objects.filter(type=Movement.Type.EXIT)
        self.assertEqual(exit_movements.count(), 2)
        
        # Verificar que se actualizó el stock
        self.lot1.refresh_from_db()
        self.lot2.refresh_from_db()
        self.assertEqual(self.lot1.qty_on_hand, Decimal('80'))  # 100 - 20
        self.assertEqual(self.lot2.qty_on_hand, Decimal('40'))  # 50 - 10
        
        # Verificar que las reservas se marcaron como aplicadas
        reservation1.refresh_from_db()
        reservation2.refresh_from_db()
        self.assertEqual(reservation1.status, Reservation.Status.APPLIED)
        self.assertEqual(reservation2.status, Reservation.Status.APPLIED)
        
        # Verificar auditoría
        audit_log = DeliveryAuditLog.objects.get(id=data['audit_log_id'])
        self.assertEqual(audit_log.order, self.order)
        self.assertEqual(audit_log.status, DeliveryAuditLog.Status.SUCCESS)
        self.assertEqual(audit_log.total_movements, 2)
        
        # Verificar items de auditoría
        audit_items = DeliveryAuditLogItem.objects.filter(audit_log=audit_log)
        self.assertEqual(audit_items.count(), 2)
    
    def test_deliver_order_single_movement(self):
        """Test: Entrega exitosa con un solo movimiento."""
        # Crear solo una reserva
        Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('15'),
            status=Reservation.Status.PENDING
        )
        
        # Ejecutar entrega con usuario autenticado
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        # Verificar respuesta exitosa
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["order_id"], self.order.id)
        self.assertEqual(data["total_movements"], 1)
        self.assertEqual(len(data["movements"]), 1)
        
        # Verificar movimiento creado
        movement = data["movements"][0]
        self.assertEqual(movement["lot_id"], self.lot1.id)
        self.assertEqual(Decimal(movement["qty_delivered"]), Decimal('15'))
        
        # Verificar que se creó el movimiento EXIT en la base de datos
        db_movement = Movement.objects.get(id=movement["movement_id"])
        self.assertEqual(db_movement.type, Movement.Type.EXIT)
        self.assertEqual(db_movement.qty, Decimal('15'))
        self.assertEqual(db_movement.lot, self.lot1)
        
        # Verificar que se actualizó el stock
        self.lot1.refresh_from_db()
        self.assertEqual(self.lot1.qty_on_hand, Decimal('85'))  # 100 - 15
        
        # Verificar que se actualizó el estado de la reserva
        reservation = Reservation.objects.get(order=self.order, lot=self.lot1)
        self.assertEqual(reservation.status, Reservation.Status.APPLIED)
        
        # Verificar auditoría
        audit_log = DeliveryAuditLog.objects.get(id=data["audit_log_id"])
        self.assertEqual(audit_log.order, self.order)
        self.assertEqual(audit_log.delivered_by, self.user)
        self.assertEqual(audit_log.status, DeliveryAuditLog.Status.SUCCESS)
        self.assertEqual(audit_log.total_movements, 1)
        
        # Verificar items de auditoría
        audit_items = DeliveryAuditLogItem.objects.filter(audit_log=audit_log)
        self.assertEqual(audit_items.count(), 1)
        audit_item = audit_items.first()
        self.assertEqual(audit_item.lot, self.lot1)
        self.assertEqual(audit_item.qty_delivered, Decimal('15'))
        self.assertEqual(audit_item.movement_id, db_movement.id)


class DeliveryErrorTestCase(DeliveryAPITestCase):
    """Pruebas para errores 409 sin efectos secundarios."""
    
    def test_deliver_order_not_found(self):
        """Test: Error 404 cuando la orden no existe."""
        response = self.client.post("/99999/deliver")
        self.assertEqual(response.status_code, 404)
    
    def test_deliver_order_no_reservations(self):
        """Test: Error 409 cuando no hay reservas activas."""
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        self.assertEqual(response.status_code, 409)
        data = response.json()
        
        self.assertEqual(data['error'], 'NO_RESERVATIONS')
        self.assertIn('no tiene reservas activas', data['detail'])
        
        # Verificar que no se crearon movimientos
        self.assertEqual(Movement.objects.count(), 0)
        
        # Verificar que el stock no cambió
        self.lot1.refresh_from_db()
        self.lot2.refresh_from_db()
        self.assertEqual(self.lot1.qty_on_hand, Decimal('100'))
        self.assertEqual(self.lot2.qty_on_hand, Decimal('50'))
    
    def test_deliver_order_insufficient_stock(self):
        """Test: Error 409 cuando no hay stock suficiente."""
        # Crear reserva que excede el stock disponible
        Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('150'),  # Más que los 100 disponibles
            status=Reservation.Status.PENDING
        )
        
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        self.assertEqual(response.status_code, 409)
        data = response.json()
        
        self.assertEqual(data['error'], 'INSUFFICIENT_STOCK')
        self.assertIn('LOT-A-001', data['detail'])
        self.assertIn('Disponible: 100', data['detail'])
        self.assertIn('Requerido: 150', data['detail'])
        self.assertEqual(data['failed_at_movement'], 1)
        
        # Verificar que no se crearon movimientos
        self.assertEqual(Movement.objects.count(), 0)
        
        # Verificar que el stock no cambió
        self.lot1.refresh_from_db()
        self.assertEqual(self.lot1.qty_on_hand, Decimal('100'))
        
        # Verificar que la reserva sigue pendiente
        reservation = Reservation.objects.get(order=self.order)
        self.assertEqual(reservation.status, Reservation.Status.PENDING)


class DeliveryRollbackTestCase(DeliveryAPITestCase):
    """Pruebas para fallos intermedios con rollback."""
    
    def test_deliver_order_rollback_on_concurrent_stock_change(self):
        """Test: Rollback cuando el stock cambia durante la transacción."""
        # Crear reservas válidas inicialmente
        reservation1 = Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('20'),
            status=Reservation.Status.PENDING
        )
        
        reservation2 = Reservation.objects.create(
            order=self.order,
            lot=self.lot2,
            qty=Decimal('10'),
            status=Reservation.Status.PENDING
        )
        
        # Simular cambio concurrente de stock (reducir stock del lot2)
        # Esto se haría normalmente por otro proceso, pero lo simulamos
        # modificando el stock justo antes de la validación interna
        
        # Reducir stock del lot2 para que falle en la segunda iteración
        self.lot2.qty_on_hand = Decimal('5')  # Menos que los 10 requeridos
        self.lot2.save()
        
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        self.assertEqual(response.status_code, 409)
        data = response.json()
        
        self.assertEqual(data['error'], 'INSUFFICIENT_STOCK')
        self.assertIn('LOT-B-001', data['detail'])
        self.assertEqual(data['failed_at_movement'], 2)
        
        # Verificar que NO se crearon movimientos (rollback completo)
        self.assertEqual(Movement.objects.count(), 0)
        
        # Verificar que el stock del lot1 NO cambió (rollback)
        self.lot1.refresh_from_db()
        self.assertEqual(self.lot1.qty_on_hand, Decimal('100'))
        
        # Verificar que las reservas siguen pendientes (rollback)
        reservation1.refresh_from_db()
        reservation2.refresh_from_db()
        self.assertEqual(reservation1.status, Reservation.Status.PENDING)
        self.assertEqual(reservation2.status, Reservation.Status.PENDING)
        
        # Verificar que NO se creó auditoría (error en validación temprana)
        audit_logs = DeliveryAuditLog.objects.filter(order=self.order)
        self.assertEqual(audit_logs.count(), 0)
    
    def test_deliver_order_rollback_preserves_original_state(self):
        """Test: El rollback preserva completamente el estado original."""
        # Estado inicial
        initial_lot1_stock = self.lot1.qty_on_hand
        initial_lot2_stock = self.lot2.qty_on_hand
        initial_movement_count = Movement.objects.count()
        initial_audit_count = DeliveryAuditLog.objects.count()
        
        # Crear reservas
        reservation1 = Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('20'),
            status=Reservation.Status.PENDING
        )
        
        reservation2 = Reservation.objects.create(
            order=self.order,
            lot=self.lot2,
            qty=Decimal('60'),  # Más que el stock disponible (50)
            status=Reservation.Status.PENDING
        )
        
        # Ejecutar entrega (debería fallar)
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        self.assertEqual(response.status_code, 409)
        
        # Verificar que TODO el estado se preservó
        self.lot1.refresh_from_db()
        self.lot2.refresh_from_db()
        
        self.assertEqual(self.lot1.qty_on_hand, initial_lot1_stock)
        self.assertEqual(self.lot2.qty_on_hand, initial_lot2_stock)
        self.assertEqual(Movement.objects.count(), initial_movement_count)
        
        # Las reservas deben seguir en su estado original
        reservation1.refresh_from_db()
        reservation2.refresh_from_db()
        self.assertEqual(reservation1.status, Reservation.Status.PENDING)
        self.assertEqual(reservation2.status, Reservation.Status.PENDING)
        
        # NO debe haberse creado auditoría (error en validación temprana)
        self.assertEqual(DeliveryAuditLog.objects.count(), initial_audit_count)


class DeliveryEdgeCasesTestCase(DeliveryAPITestCase):
    """Pruebas para casos edge y validaciones adicionales."""
    
    def test_deliver_order_with_applied_reservations(self):
        """Test: Entrega con reservas ya aplicadas (debería incluirlas)."""
        # Crear reservas con diferentes estados
        reservation1 = Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('20'),
            status=Reservation.Status.PENDING
        )
        
        reservation2 = Reservation.objects.create(
            order=self.order,
            lot=self.lot2,
            qty=Decimal('10'),
            status=Reservation.Status.APPLIED  # Ya aplicada
        )
        
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Debe procesar ambas reservas (PENDING y APPLIED)
        self.assertEqual(data['total_movements'], 2)
    
    def test_deliver_order_ignores_cancelled_reservations(self):
        """Test: Entrega ignora reservas canceladas."""
        # Crear reservas con diferentes estados
        Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('20'),
            status=Reservation.Status.PENDING
        )
        
        Reservation.objects.create(
            order=self.order,
            lot=self.lot2,
            qty=Decimal('10'),
            status=Reservation.Status.CANCELLED  # Cancelada
        )
        
        with patch('apps.orders.picking_api.getattr') as mock_getattr:
            mock_getattr.return_value = self.user
            response = self.client.post(f"/{self.order.id}/deliver")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Solo debe procesar la reserva PENDING
        self.assertEqual(data['total_movements'], 1)
        
        # Verificar que solo se movió stock del lot1
        self.lot1.refresh_from_db()
        self.lot2.refresh_from_db()
        self.assertEqual(self.lot1.qty_on_hand, Decimal('80'))  # 100 - 20
        self.assertEqual(self.lot2.qty_on_hand, Decimal('50'))  # Sin cambios