"""
Ejemplo de test unitario.
Tests rápidos y aislados que no requieren base de datos.
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
class TestExampleUnit:
    """Ejemplo de clase de test unitario."""
    
    def test_simple_calculation(self):
        """Test simple sin dependencias externas."""
        result = 2 + 2
        assert result == 4
    
    @patch('some.external.dependency')
    def test_with_mock(self, mock_dependency):
        """Test usando mocks para aislar dependencias."""
        mock_dependency.return_value = "mocked_value"
        
        # Tu lógica de test aquí
        assert mock_dependency() == "mocked_value"
        mock_dependency.assert_called_once()
    
    def test_edge_case(self):
        """Test de casos límite."""
        # Ejemplo de test de caso límite
        assert [] == []
        assert len([]) == 0
