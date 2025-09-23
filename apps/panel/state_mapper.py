"""
Mapper de estados entre dominio y panel
Maneja las transiciones válidas y conversiones bidireccionales
"""

from typing import Dict, Set, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class DomainStatus(Enum):
    """Estados del dominio (modelo Order)."""
    DRAFT = "draft"
    PLACED = "placed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PanelStatus(Enum):
    """Estados del panel (interfaz administrativa)."""
    DRAFT = "DRAFT"
    NEW = "NEW"
    PICKING = "PICKING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

# Mapeo de estados del dominio al panel
DOMAIN_TO_PANEL: Dict[str, str] = {
    DomainStatus.DRAFT.value: PanelStatus.NEW.value,
    DomainStatus.PLACED.value: PanelStatus.NEW.value,
    DomainStatus.PROCESSING.value: PanelStatus.PICKING.value,
    DomainStatus.SHIPPED.value: PanelStatus.READY.value,
    DomainStatus.DELIVERED.value: PanelStatus.DELIVERED.value,
    DomainStatus.CANCELLED.value: PanelStatus.CANCELLED.value,
}

# Mapeo inverso: del panel al dominio
PANEL_TO_DOMAIN: Dict[str, str] = {
    PanelStatus.NEW.value: DomainStatus.PLACED.value,  # Asumimos PLACED como estado principal para NEW
    PanelStatus.PICKING.value: DomainStatus.PROCESSING.value,
    PanelStatus.READY.value: DomainStatus.SHIPPED.value,
    PanelStatus.DELIVERED.value: DomainStatus.DELIVERED.value,
    PanelStatus.CANCELLED.value: DomainStatus.CANCELLED.value,
}

# Matriz de transiciones válidas en el panel
# Formato: estado_actual → {estados_permitidos}
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    PanelStatus.NEW.value: {PanelStatus.PICKING.value, PanelStatus.CANCELLED.value, PanelStatus.NEW.value},
    PanelStatus.PICKING.value: {PanelStatus.READY.value, PanelStatus.CANCELLED.value, PanelStatus.PICKING.value},
    PanelStatus.READY.value: {PanelStatus.DELIVERED.value, PanelStatus.CANCELLED.value},
    PanelStatus.DELIVERED.value: set(),  # Estado final
    PanelStatus.CANCELLED.value: set(),  # Estado final
}

def domain_to_panel(domain_status):
    """
    Convierte estado del dominio a estado del panel.
    
    Args:
        domain_status: Estado del modelo Order (puede ser string o enum)
        
    Returns:
        Estado correspondiente en el panel (enum PanelStatus)
        
    Raises:
        ValueError: Si el estado del dominio no es válido
    """
    # Convertir enum a string si es necesario
    if hasattr(domain_status, 'value'):
        domain_status = domain_status.value
    
    if domain_status not in DOMAIN_TO_PANEL:
        raise ValueError(f"Unknown domain status: {domain_status}")
    
    panel_status_str = DOMAIN_TO_PANEL[domain_status]
    # Retornar el enum correspondiente
    panel_status = PanelStatus(panel_status_str)
    logger.debug(f"Mapped domain status {domain_status} → panel status {panel_status}")
    return panel_status

def panel_to_domain(panel_status):
    """
    Convierte estado del panel a estado del dominio.
    
    Args:
        panel_status: Estado del panel (puede ser string o enum)
        
    Returns:
        Estado correspondiente en el dominio (enum DomainStatus)
        
    Raises:
        ValueError: Si el estado del panel no es válido
    """
    # Convertir enum a string si es necesario
    if hasattr(panel_status, 'value'):
        panel_status = panel_status.value
    
    if panel_status not in PANEL_TO_DOMAIN:
        raise ValueError(f"Unknown panel status: {panel_status}")
    
    domain_status_str = PANEL_TO_DOMAIN[panel_status]
    # Retornar el enum correspondiente
    domain_status = DomainStatus(domain_status_str)
    logger.debug(f"Mapped panel status {panel_status} → domain status {domain_status}")
    return domain_status

def is_valid_transition(current_status: str, new_status: str) -> bool:
    """
    Verifica si una transición de estado es válida.
    
    Args:
        current_status: Estado actual del panel
        new_status: Estado destino del panel
        
    Returns:
        True si la transición es válida, False en caso contrario
    """
    if current_status not in VALID_TRANSITIONS:
        logger.warning(f"Estado actual inválido: {current_status}")
        return False
    
    is_valid = new_status in VALID_TRANSITIONS[current_status]
    
    if is_valid:
        logger.info(f"Valid transition: {current_status} → {new_status}")
    else:
        logger.warning(f"Invalid transition attempted: {current_status} → {new_status}")
    
    return is_valid

def get_valid_next_states(current_status) -> Set:
    """
    Obtiene los estados válidos desde el estado actual.
    
    Args:
        current_status: Estado actual del panel (string o enum)
        
    Returns:
        Conjunto de estados válidos como destino (enums PanelStatus)
    """
    # Convertir enum a string si es necesario
    if hasattr(current_status, 'value'):
        current_status = current_status.value
    
    if current_status not in VALID_TRANSITIONS:
        logger.warning(f"Estado actual inválido: {current_status}")
        return set()
    
    # Convertir strings a enums
    valid_states = set()
    for state_str in VALID_TRANSITIONS[current_status]:
        valid_states.add(PanelStatus(state_str))
    
    return valid_states

class StateTransitionError(Exception):
    """Excepción para transiciones de estado inválidas."""
    
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Transición inválida: {current_status} → {new_status}")

def validate_and_map_transition(
    current_domain_status, 
    new_panel_status
) -> Tuple:
    """
    Valida una transición y retorna los estados mapeados.
    
    Args:
        current_domain_status: Estado actual en el dominio (string o enum)
        new_panel_status: Estado destino en el panel (string o enum)
        
    Returns:
        Tupla (current_panel_status_enum, new_domain_status_enum)
        
    Raises:
        StateTransitionError: Si la transición no es válida
        ValueError: Si algún estado es inválido
    """
    # Convertir enums a strings si es necesario
    if hasattr(current_domain_status, 'value'):
        current_domain_status = current_domain_status.value
    if hasattr(new_panel_status, 'value'):
        new_panel_status = new_panel_status.value
    
    # Mapear estado actual a panel (obtenemos enum)
    current_panel_status_enum = domain_to_panel(current_domain_status)
    current_panel_status = current_panel_status_enum.value
    
    # Validar transición
    if not is_valid_transition(current_panel_status, new_panel_status):
        raise StateTransitionError(current_panel_status, new_panel_status)
    
    # Mapear nuevo estado a dominio (obtenemos enum)
    new_domain_status_enum = panel_to_domain(new_panel_status)
    
    logger.info(
        f"Validated transition: {current_domain_status}({current_panel_status}) → "
        f"{new_domain_status_enum.value}({new_panel_status})"
    )
    
    return current_panel_status_enum, new_domain_status_enum