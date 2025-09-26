"""
Tests unitarios para los servicios de stock.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from apps.catalog.models import Product
from apps.stock.models import StockLot, Movement, Warehouse
from apps.stock.services import (
    create_entry, 
    StockError, 
    NotEnoughStock, 
    NoLotsAvailable,
    LotOption,
    AllocationPlan
)


@pytest.mark.unit
@pytest.mark.django_db
class TestStockServices:
    """Tests para los servicios de stock."""
    
    def setup_method(self):
        """Setup para cada test."""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.warehouse = Warehouse.objects.create(name="Test Warehouse")
        self.product = Product.objects.create(
            code="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            tax_rate=Decimal("21.00")
        )
    
    def test_create_entry_success(self):
        """Test creación exitosa de entrada de stock."""
        movement = create_entry(
            product=self.product,
            lot_code="LOT-001",
            expiry_date=date.today() + timedelta(days=30),
            qty=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        assert movement.id is not None
        assert movement.type == Movement.Type.ENTRY
        assert movement.product == self.product
        assert movement.qty == Decimal("10.00")
        assert movement.unit_cost == Decimal("8.00")
        assert movement.created_by == self.user
        
        # Verificar que se creó el lote
        stock_lot = StockLot.objects.get(lot_code="LOT-001")
        assert stock_lot.qty_on_hand == Decimal("10.00")
        assert stock_lot.product == self.product
        assert stock_lot.warehouse == self.warehouse
    
    def test_create_entry_invalid_qty(self):
        """Test error al crear entrada con cantidad inválida."""
        with pytest.raises(StockError) as exc_info:
            create_entry(
                product=self.product,
                lot_code="LOT-002",
                expiry_date=date.today() + timedelta(days=30),
                qty=Decimal("0"),
                unit_cost=Decimal("8.00"),
                warehouse=self.warehouse,
                created_by=self.user
            )
        
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "cantidad debe ser mayor a 0" in str(exc_info.value)
    
    def test_create_entry_invalid_unit_cost(self):
        """Test error al crear entrada con costo unitario inválido."""
        with pytest.raises(StockError) as exc_info:
            create_entry(
                product=self.product,
                lot_code="LOT-003",
                expiry_date=date.today() + timedelta(days=30),
                qty=Decimal("10.00"),
                unit_cost=Decimal("0"),
                warehouse=self.warehouse,
                created_by=self.user
            )
        
        assert exc_info.value.code == "VALIDATION_ERROR"
        assert "costo unitario debe ser mayor a 0" in str(exc_info.value)
    
    def test_create_entry_existing_lot_same_expiry(self):
        """Test creación de entrada para lote existente con misma fecha de vencimiento."""
        expiry_date = date.today() + timedelta(days=30)
        
        # Crear primera entrada
        create_entry(
            product=self.product,
            lot_code="LOT-004",
            expiry_date=expiry_date,
            qty=Decimal("5.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Crear segunda entrada para el mismo lote
        create_entry(
            product=self.product,
            lot_code="LOT-004",
            expiry_date=expiry_date,
            qty=Decimal("3.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Verificar que se acumuló la cantidad
        stock_lot = StockLot.objects.get(lot_code="LOT-004")
        assert stock_lot.qty_on_hand == Decimal("8.00")
    
    def test_create_entry_existing_lot_different_expiry(self):
        """Test error al crear entrada para lote existente con diferente fecha de vencimiento."""
        expiry_date1 = date.today() + timedelta(days=30)
        expiry_date2 = date.today() + timedelta(days=60)
        
        # Crear primera entrada
        create_entry(
            product=self.product,
            lot_code="LOT-005",
            expiry_date=expiry_date1,
            qty=Decimal("5.00"),
            unit_cost=Decimal("8.00"),
            warehouse=self.warehouse,
            created_by=self.user
        )
        
        # Intentar crear segunda entrada con diferente fecha de vencimiento
        with pytest.raises(StockError) as exc_info:
            create_entry(
                product=self.product,
                lot_code="LOT-005",
                expiry_date=expiry_date2,
                qty=Decimal("3.00"),
                unit_cost=Decimal("8.00"),
                warehouse=self.warehouse,
                created_by=self.user
            )
        
        assert exc_info.value.code == "INCONSISTENT_LOT"
        assert "ya existe con fecha de vencimiento" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.django_db
class TestStockExceptions:
    """Tests para las excepciones de stock."""
    
    def test_not_enough_stock_exception(self):
        """Test excepción NotEnoughStock."""
        exc = NotEnoughStock(
            product_id=1,
            requested=Decimal("10.00"),
            available=Decimal("5.00")
        )
        
        assert exc.code == "NOT_ENOUGH_STOCK"
        assert exc.product_id == 1
        assert exc.requested == Decimal("10.00")
        assert exc.available == Decimal("5.00")
        assert "Stock insuficiente" in str(exc)
    
    def test_no_lots_available_exception(self):
        """Test excepción NoLotsAvailable."""
        exc = NoLotsAvailable(product_id=1, criteria="no vencidos")
        
        assert exc.code == "NO_LOTS_AVAILABLE"
        assert exc.product_id == 1
        assert exc.criteria == "no vencidos"
        assert "No hay lotes disponibles" in str(exc)
    
    def test_no_lots_available_exception_no_criteria(self):
        """Test excepción NoLotsAvailable sin criterios."""
        exc = NoLotsAvailable(product_id=1)
        
        assert exc.code == "NO_LOTS_AVAILABLE"
        assert exc.product_id == 1
        assert exc.criteria == ""
        assert "No hay lotes disponibles" in str(exc)


@pytest.mark.unit
class TestStockDataStructures:
    """Tests para las estructuras de datos de stock."""
    
    def test_lot_option_creation(self):
        """Test creación de LotOption."""
        lot_option = LotOption(
            lot_id=1,
            lot_code="LOT-001",
            expiry_date=date.today(),
            qty_available=Decimal("10.00"),
            unit_cost=Decimal("8.00"),
            warehouse_name="Test Warehouse"
        )
        
        assert lot_option.lot_id == 1
        assert lot_option.lot_code == "LOT-001"
        assert lot_option.qty_available == Decimal("10.00")
        assert lot_option.unit_cost == Decimal("8.00")
        assert lot_option.warehouse_name == "Test Warehouse"
    
    def test_allocation_plan_creation(self):
        """Test creación de AllocationPlan."""
        plan = AllocationPlan(
            lot_id=1,
            qty_allocated=Decimal("5.00")
        )
        
        assert plan.lot_id == 1
        assert plan.qty_allocated == Decimal("5.00")