"""
Tests para el mapper de estados dominio ↔ panel
Incluye tests de round-trip y validación de transiciones
"""

import pytest
from apps.panel.state_mapper import (
    DomainStatus,
    PanelStatus,
    domain_to_panel,
    panel_to_domain,
    validate_and_map_transition,
    get_valid_next_states,
    StateTransitionError,
    DOMAIN_TO_PANEL,
    PANEL_TO_DOMAIN,
    VALID_TRANSITIONS
)

class TestStateMapper:
    """Tests para el mapper de estados."""
    
    def test_domain_to_panel_mapping(self):
        """Test mapeo de estados del dominio al panel."""
        # Estados válidos
        assert domain_to_panel(DomainStatus.DRAFT) == PanelStatus.NEW
        assert domain_to_panel(DomainStatus.PLACED) == PanelStatus.NEW
        assert domain_to_panel(DomainStatus.PROCESSING) == PanelStatus.PICKING
        assert domain_to_panel(DomainStatus.SHIPPED) == PanelStatus.READY
        assert domain_to_panel(DomainStatus.DELIVERED) == PanelStatus.DELIVERED
        assert domain_to_panel(DomainStatus.CANCELLED) == PanelStatus.CANCELLED
        
        # Estado inválido
        with pytest.raises(ValueError, match="Unknown domain status"):
            domain_to_panel("INVALID_STATUS")
    
    def test_panel_to_domain_mapping(self):
        """Test mapeo de estados del panel al dominio."""
        # Estados válidos
        assert panel_to_domain(PanelStatus.NEW) == DomainStatus.PLACED
        assert panel_to_domain(PanelStatus.PICKING) == DomainStatus.PROCESSING
        assert panel_to_domain(PanelStatus.READY) == DomainStatus.SHIPPED
        assert panel_to_domain(PanelStatus.DELIVERED) == DomainStatus.DELIVERED
        assert panel_to_domain(PanelStatus.CANCELLED) == DomainStatus.CANCELLED
        
        # Estado inválido
        with pytest.raises(ValueError, match="Unknown panel status"):
            panel_to_domain("INVALID_STATUS")
    
    def test_round_trip_mapping(self):
        """Test de round-trip: dominio → panel → dominio."""
        # Para estados que tienen mapeo directo
        test_cases = [
            (DomainStatus.PROCESSING, PanelStatus.PICKING),
            (DomainStatus.SHIPPED, PanelStatus.READY),
            (DomainStatus.DELIVERED, PanelStatus.DELIVERED),
            (DomainStatus.CANCELLED, PanelStatus.CANCELLED),
        ]
        
        for domain_status, expected_panel_status in test_cases:
            # Dominio → Panel
            panel_status = domain_to_panel(domain_status)
            assert panel_status == expected_panel_status
            
            # Panel → Dominio (round-trip)
            back_to_domain = panel_to_domain(panel_status)
            assert back_to_domain == domain_status
    
    def test_special_case_new_status(self):
        """Test caso especial: DRAFT y PLACED mapean a NEW."""
        # Ambos DRAFT y PLACED mapean a NEW
        assert domain_to_panel(DomainStatus.DRAFT) == PanelStatus.NEW
        assert domain_to_panel(DomainStatus.PLACED) == PanelStatus.NEW
        
        # NEW mapea de vuelta a PLACED (estado más común)
        assert panel_to_domain(PanelStatus.NEW) == DomainStatus.PLACED
    
    def test_valid_transitions(self):
        """Test transiciones válidas del panel."""
        # NEW puede ir a PICKING o CANCELLED
        valid_from_new = get_valid_next_states(PanelStatus.NEW)
        assert PanelStatus.PICKING in valid_from_new
        assert PanelStatus.CANCELLED in valid_from_new
        assert len(valid_from_new) == 2
        
        # PICKING puede ir a READY o CANCELLED
        valid_from_picking = get_valid_next_states(PanelStatus.PICKING)
        assert PanelStatus.READY in valid_from_picking
        assert PanelStatus.CANCELLED in valid_from_picking
        assert len(valid_from_picking) == 2
        
        # READY puede ir a DELIVERED o CANCELLED
        valid_from_ready = get_valid_next_states(PanelStatus.READY)
        assert PanelStatus.DELIVERED in valid_from_ready
        assert PanelStatus.CANCELLED in valid_from_ready
        assert len(valid_from_ready) == 2
        
        # Estados finales no tienen transiciones
        assert len(get_valid_next_states(PanelStatus.DELIVERED)) == 0
        assert len(get_valid_next_states(PanelStatus.CANCELLED)) == 0
    
    def test_validate_and_map_transition_success(self):
        """Test validación exitosa de transiciones."""
        # NEW → PICKING
        old_panel, new_domain = validate_and_map_transition(
            DomainStatus.PLACED, PanelStatus.PICKING
        )
        assert old_panel == PanelStatus.NEW
        assert new_domain == DomainStatus.PROCESSING
        
        # PICKING → READY
        old_panel, new_domain = validate_and_map_transition(
            DomainStatus.PROCESSING, PanelStatus.READY
        )
        assert old_panel == PanelStatus.PICKING
        assert new_domain == DomainStatus.SHIPPED
        
        # Cualquier estado → CANCELLED
        old_panel, new_domain = validate_and_map_transition(
            DomainStatus.PROCESSING, PanelStatus.CANCELLED
        )
        assert old_panel == PanelStatus.PICKING
        assert new_domain == DomainStatus.CANCELLED
    
    def test_validate_and_map_transition_invalid(self):
        """Test validación de transiciones inválidas."""
        # NEW → DELIVERED (saltar estados)
        with pytest.raises(StateTransitionError, match="Invalid transition"):
            validate_and_map_transition(DomainStatus.PLACED, PanelStatus.DELIVERED)
        
        # DELIVERED → PICKING (retroceder)
        with pytest.raises(StateTransitionError, match="Invalid transition"):
            validate_and_map_transition(DomainStatus.DELIVERED, PanelStatus.PICKING)
        
        # CANCELLED → cualquier otro (estado final)
        with pytest.raises(StateTransitionError, match="Invalid transition"):
            validate_and_map_transition(DomainStatus.CANCELLED, PanelStatus.PICKING)
    
    def test_validate_and_map_transition_same_status(self):
        """Test transición al mismo estado (idempotencia)."""
        # Mismo estado debe ser válido (idempotencia)
        old_panel, new_domain = validate_and_map_transition(
            DomainStatus.PROCESSING, PanelStatus.PICKING
        )
        assert old_panel == PanelStatus.PICKING
        assert new_domain == DomainStatus.PROCESSING
    
    def test_invalid_status_values(self):
        """Test manejo de valores de estado inválidos."""
        # Estado del dominio inválido
        with pytest.raises(ValueError):
            validate_and_map_transition("INVALID_DOMAIN", PanelStatus.PICKING)
        
        # Estado del panel inválido
        with pytest.raises(ValueError):
            validate_and_map_transition(DomainStatus.PLACED, "INVALID_PANEL")
    
    def test_mapping_dictionaries_consistency(self):
        """Test consistencia de los diccionarios de mapeo."""
        # Verificar que todos los estados del dominio tienen mapeo
        for domain_status in DomainStatus:
            assert domain_status in DOMAIN_TO_PANEL
        
        # Verificar que todos los estados del panel tienen mapeo
        for panel_status in PanelStatus:
            assert panel_status in PANEL_TO_DOMAIN
        
        # Verificar que todos los estados del panel tienen transiciones definidas
        for panel_status in PanelStatus:
            assert panel_status.value in VALID_TRANSITIONS
    
    def test_transition_matrix_completeness(self):
        """Test completitud de la matriz de transiciones."""
        # Verificar que todos los estados no finales tienen al menos CANCELLED
        non_final_states = [PanelStatus.NEW, PanelStatus.PICKING, PanelStatus.READY]
        
        for status in non_final_states:
            valid_transitions = VALID_TRANSITIONS[status.value]
            assert PanelStatus.CANCELLED.value in valid_transitions, f"{status} should allow CANCELLED"
        
        # Verificar que los estados finales no tienen transiciones
        final_states = [PanelStatus.DELIVERED, PanelStatus.CANCELLED]
        
        for status in final_states:
            valid_transitions = VALID_TRANSITIONS[status.value]
            assert len(valid_transitions) == 0, f"{status} should not have transitions"

class TestStateMapperIntegration:
    """Tests de integración para el mapper de estados."""
    
    def test_complete_workflow_happy_path(self):
        """Test flujo completo exitoso: NEW → PICKING → READY → DELIVERED."""
        current_domain = DomainStatus.PLACED
        
        # NEW → PICKING
        old_panel, current_domain = validate_and_map_transition(
            current_domain, PanelStatus.PICKING
        )
        assert old_panel == PanelStatus.NEW
        assert current_domain == DomainStatus.PROCESSING
        
        # PICKING → READY
        old_panel, current_domain = validate_and_map_transition(
            current_domain, PanelStatus.READY
        )
        assert old_panel == PanelStatus.PICKING
        assert current_domain == DomainStatus.SHIPPED
        
        # READY → DELIVERED
        old_panel, current_domain = validate_and_map_transition(
            current_domain, PanelStatus.DELIVERED
        )
        assert old_panel == PanelStatus.READY
        assert current_domain == DomainStatus.DELIVERED
    
    def test_cancellation_from_any_state(self):
        """Test cancelación desde cualquier estado."""
        states_to_test = [
            DomainStatus.PLACED,
            DomainStatus.PROCESSING,
            DomainStatus.SHIPPED,
        ]
        
        for domain_status in states_to_test:
            old_panel, new_domain = validate_and_map_transition(
                domain_status, PanelStatus.CANCELLED
            )
            assert new_domain == DomainStatus.CANCELLED
            # El estado del panel anterior debe ser el mapeo correcto
            expected_old_panel = domain_to_panel(domain_status)
            assert old_panel == expected_old_panel