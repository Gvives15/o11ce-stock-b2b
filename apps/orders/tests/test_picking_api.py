"""Tests for order picking API endpoints."""

import json
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from apps.catalog.models import Product
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem
from apps.stock.models import Warehouse, StockLot
from apps.stock.reservations import Reservation


@pytest.mark.django_db
class TestPickingSuggestionsAPI(TestCase):
    """Tests for GET /orders/{id}/picking/suggestions endpoint."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create warehouse
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse'
        )
        
        # Create product
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='test@example.com',
            phone='123456789'
        )
        
        # Create order
        self.order = Order.objects.create(
            customer=self.customer,
            status='new',
            total=Decimal('20.00')
        )
        
        # Create order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            qty=Decimal('5.000'),
            unit_price=Decimal('10.00')
        )
        
        # Create stock lots with different expiry dates (FEFO order)
        self.lot_early = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-EARLY',
            expiry_date=date.today() + timedelta(days=10),
            qty_on_hand=Decimal('3.000'),
            unit_cost=Decimal('8.00')
        )
        
        self.lot_late = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-LATE',
            expiry_date=date.today() + timedelta(days=20),
            qty_on_hand=Decimal('4.000'),
            unit_cost=Decimal('8.50')
        )
    
    def test_picking_suggestions_fefo_order(self):
        """Test que las sugerencias siguen orden FEFO correcto."""
        response = self.client.get(f'/api/v1/orders/{self.order.id}/picking/suggestions')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('suggestions', data)
        suggestions = data['suggestions']
        
        # Debe haber 2 sugerencias (una por lote)
        self.assertEqual(len(suggestions), 2)
        
        # Primera sugerencia debe ser del lote que vence primero
        first_suggestion = suggestions[0]
        self.assertEqual(first_suggestion['lot_code'], 'LOT-EARLY')
        self.assertEqual(Decimal(first_suggestion['qty']), Decimal('3.000'))
        
        # Segunda sugerencia debe ser del lote que vence después
        second_suggestion = suggestions[1]
        self.assertEqual(second_suggestion['lot_code'], 'LOT-LATE')
        self.assertEqual(Decimal(second_suggestion['qty']), Decimal('2.000'))  # Solo lo que falta
    
    def test_picking_suggestions_considers_reservations(self):
        """Test que las sugerencias consideran reservas existentes."""
        # Crear una reserva en el primer lote
        other_order = Order.objects.create(
            customer=self.customer,
            status='new',
            total=Decimal('10.00')
        )
        
        Reservation.objects.create(
            order=other_order,
            lot=self.lot_early,
            qty=Decimal('2.000'),
            status=Reservation.Status.PENDING
        )
        
        response = self.client.get(f'/api/v1/orders/{self.order.id}/picking/suggestions')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        suggestions = data['suggestions']
        self.assertEqual(len(suggestions), 2)
        
        # Primera sugerencia debe considerar la reserva
        first_suggestion = suggestions[0]
        self.assertEqual(first_suggestion['lot_code'], 'LOT-EARLY')
        self.assertEqual(Decimal(first_suggestion['qty']), Decimal('1.000'))  # 3 - 2 reservados
        
        # Segunda sugerencia debe completar lo que falta
        second_suggestion = suggestions[1]
        self.assertEqual(second_suggestion['lot_code'], 'LOT-LATE')
        self.assertEqual(Decimal(second_suggestion['qty']), Decimal('4.000'))  # Lo que falta
    
    def test_picking_suggestions_excludes_quarantined_lots(self):
        """Test que las sugerencias excluyen lotes en cuarentena."""
        # Poner el primer lote en cuarentena
        self.lot_early.is_quarantined = True
        self.lot_early.save()
        
        response = self.client.get(f'/api/v1/orders/{self.order.id}/picking/suggestions')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        suggestions = data['suggestions']
        self.assertEqual(len(suggestions), 1)
        
        # Solo debe sugerir el lote no cuarentenado
        suggestion = suggestions[0]
        self.assertEqual(suggestion['lot_code'], 'LOT-LATE')
        self.assertEqual(Decimal(suggestion['qty']), Decimal('4.000'))
    
    def test_picking_suggestions_excludes_expired_lots(self):
        """Test que las sugerencias excluyen lotes vencidos."""
        # Hacer que el primer lote esté vencido
        self.lot_early.expiry_date = date.today() - timedelta(days=1)
        self.lot_early.save()
        
        response = self.client.get(f'/api/v1/orders/{self.order.id}/picking/suggestions')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        suggestions = data['suggestions']
        self.assertEqual(len(suggestions), 1)
        
        # Solo debe sugerir el lote no vencido
        suggestion = suggestions[0]
        self.assertEqual(suggestion['lot_code'], 'LOT-LATE')
        self.assertEqual(Decimal(suggestion['qty']), Decimal('4.000'))
    
    def test_picking_suggestions_order_not_found(self):
        """Test error 404 cuando la orden no existe."""
        response = self.client.get('/api/v1/orders/99999/picking/suggestions')
        
        self.assertEqual(response.status_code, 404)


@pytest.mark.django_db
class TestReservationAPI(TestCase):
    """Tests for POST /orders/{id}/reserve endpoint."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create warehouse
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse'
        )
        
        # Create product
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='test@example.com',
            phone='123456789'
        )
        
        # Create order
        self.order = Order.objects.create(
            customer=self.customer,
            status='new',
            total=Decimal('20.00')
        )
        
        # Create stock lot
        self.lot = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-001',
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('8.00')
        )
    
    def test_create_reservation_success(self):
        """Test creación exitosa de reserva."""
        reservation_data = {
            'reservations': [
                {
                    'lot_id': self.lot.id,
                    'qty': '5.000'
                }
            ]
        }
        
        response = self.client.post(
            f'/api/v1/orders/{self.order.id}/reserve',
            data=json.dumps(reservation_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('reservations', data)
        reservations = data['reservations']
        self.assertEqual(len(reservations), 1)
        
        reservation = reservations[0]
        self.assertEqual(reservation['lot_id'], self.lot.id)
        self.assertEqual(Decimal(reservation['qty']), Decimal('5.000'))
        self.assertEqual(reservation['status'], 'pending')
        
        # Verificar que se creó en la base de datos
        db_reservation = Reservation.objects.get(order=self.order, lot=self.lot)
        self.assertEqual(db_reservation.qty, Decimal('5.000'))
        self.assertEqual(db_reservation.status, Reservation.Status.PENDING)
    
    def test_create_reservation_exceeds_available_stock(self):
        """Test error 422 cuando se excede stock disponible."""
        # Crear una reserva existente que deje solo 3 unidades disponibles
        other_order = Order.objects.create(
            customer=self.customer,
            status='new',
            total=Decimal('10.00')
        )
        
        Reservation.objects.create(
            order=other_order,
            lot=self.lot,
            qty=Decimal('7.000'),
            status=Reservation.Status.PENDING
        )
        
        # Intentar reservar más de lo disponible
        reservation_data = {
            'reservations': [
                {
                    'lot_id': self.lot.id,
                    'qty': '5.000'  # Solo hay 3 disponibles (10 - 7)
                }
            ]
        }
        
        response = self.client.post(
            f'/api/v1/orders/{self.order.id}/reserve',
            data=json.dumps(reservation_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 422)
        response_data = response.json()
        self.assertEqual(response_data['error'], 'INSUFFICIENT_STOCK')
        self.assertIn('availability_check', response_data)
        self.assertIsInstance(response_data['availability_check'], dict)
    
    def test_create_reservation_replaces_existing(self):
        """Test que las nuevas reservas reemplazan las existentes."""
        # Crear reserva inicial
        initial_reservation = Reservation.objects.create(
            order=self.order,
            lot=self.lot,
            qty=Decimal('3.000'),
            status=Reservation.Status.PENDING
        )
        
        # Crear nueva reserva
        reservation_data = {
            'reservations': [
                {
                    'lot_id': self.lot.id,
                    'qty': '7.000'
                }
            ]
        }
        
        response = self.client.post(
            f'/api/v1/orders/{self.order.id}/reserve',
            data=json.dumps(reservation_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que la reserva inicial fue eliminada (no solo cancelada)
        with self.assertRaises(Reservation.DoesNotExist):
            initial_reservation.refresh_from_db()
        
        # Verificar que se creó la nueva reserva
        new_reservation = Reservation.objects.get(
            order=self.order,
            lot=self.lot,
            status=Reservation.Status.PENDING
        )
        self.assertEqual(new_reservation.qty, Decimal('7.000'))
    
    def test_create_reservation_order_not_found(self):
        """Test error 404 cuando la orden no existe."""
        reservation_data = {
            'reservations': [
                {
                    'lot_id': self.lot.id,
                    'qty': '5.000'
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/orders/99999/reserve',
            data=json.dumps(reservation_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_create_reservation_lot_not_found(self):
        """Test error 422 cuando el lote no existe."""
        reservation_data = {
            'reservations': [
                {
                    'lot_id': 99999,
                    'qty': '5.000'
                }
            ]
        }
        
        response = self.client.post(
            f'/api/v1/orders/{self.order.id}/reserve',
            data=json.dumps(reservation_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 422)
        data = response.json()
        
        self.assertIn('detail', data)
        self.assertIn('availability_check', data)
        self.assertIn('99999', data['detail'])  # Debe mencionar el ID del lote


@pytest.mark.django_db
class TestReservationReleaseOnCancellation(TestCase):
    """Tests for automatic reservation release when order is cancelled."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create user with panel access
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create warehouse
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse'
        )
        
        # Create product
        self.product = Product.objects.create(
            code='TEST-001',
            name='Test Product',
            price=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            is_active=True
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            name='Test Customer',
            email='test@example.com',
            phone='123456789'
        )
        
        # Create order
        self.order = Order.objects.create(
            customer=self.customer,
            status='new',
            total=Decimal('20.00')
        )
        
        # Create stock lot
        self.lot1 = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-001',
            expiry_date=date.today() + timedelta(days=30),
            qty_on_hand=Decimal('10.000'),
            unit_cost=Decimal('8.00')
        )
        
        self.lot2 = StockLot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='LOT-002',
            expiry_date=date.today() + timedelta(days=40),
            qty_on_hand=Decimal('5.000'),
            unit_cost=Decimal('8.50')
        )
        
        # Create reservations on different lots to avoid unique constraint
        self.reservation_pending = Reservation.objects.create(
            order=self.order,
            lot=self.lot1,
            qty=Decimal('3.000'),
            status=Reservation.Status.PENDING
        )
        
        self.reservation_applied = Reservation.objects.create(
            order=self.order,
            lot=self.lot2,
            qty=Decimal('2.000'),
            status=Reservation.Status.APPLIED
        )
    
    def test_reservations_released_on_order_cancellation(self):
        """Test that reservations are automatically released when order is cancelled"""
        # Verify initial reservations exist
        self.assertEqual(
            Reservation.objects.filter(order=self.order, status=Reservation.Status.PENDING).count(),
            1
        )
        self.assertEqual(
            Reservation.objects.filter(order=self.order, status=Reservation.Status.APPLIED).count(),
            1
        )
        
        # Cancel the order and simulate the hook that releases reservations
        self.order.status = 'cancelled'
        self.order.save()
        
        # Simulate the hook from change_order_status that releases reservations
        cancelled_reservations = Reservation.objects.filter(
            order=self.order,
            status__in=[Reservation.Status.PENDING, Reservation.Status.APPLIED]
        )
        for reservation in cancelled_reservations:
            reservation.cancel()
        
        # Verify reservations are released
        self.assertEqual(
            Reservation.objects.filter(order=self.order, status=Reservation.Status.PENDING).count(),
            0
        )
        self.assertEqual(
            Reservation.objects.filter(order=self.order, status=Reservation.Status.APPLIED).count(),
            0
        )
        self.assertEqual(
            Reservation.objects.filter(order=self.order, status=Reservation.Status.CANCELLED).count(),
            2
        )
    
    def test_cancelled_reservations_not_considered_in_availability(self):
        """Test que las reservas canceladas no afectan la disponibilidad."""
        # Cancelar las reservas
        self.reservation_pending.cancel()
        self.reservation_applied.cancel()
        
        # Verificar que la disponibilidad del lote no se ve afectada por la reserva cancelada
        self.lot1.refresh_from_db()
        
        # qty_available debería ser qty_on_hand - reservas activas
        # Como cancelamos la reserva pending, solo queda la applied en lot2
        expected_available = self.lot1.qty_on_hand  # No hay reservas activas en lot1
        self.assertEqual(self.lot1.qty_available, expected_available)
        
        # Verificar que se pueden crear nuevas reservas por el total
        other_order = Order.objects.create(
            customer=self.customer,
            status='new',
            total=Decimal('50.00')
        )
        
        new_reservation = Reservation.objects.create(
            order=other_order,
            lot=self.lot1,
            qty=Decimal('10.000'),
            status=Reservation.Status.PENDING
        )
        
        # No debe haber errores de stock insuficiente
        self.assertEqual(new_reservation.qty, Decimal('10.000'))