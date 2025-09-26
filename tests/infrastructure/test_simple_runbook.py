"""
Test simple para verificar que el RUNBOOK existe y tiene contenido básico.
"""
import os
import re
from pathlib import Path


def test_runbook_exists():
    """Test que el archivo RUNBOOK existe."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    assert runbook_path.exists(), "RUNBOOK_FINAL.md debe existir en la raíz del proyecto"
    print("✅ RUNBOOK_FINAL.md existe")


def test_runbook_has_content():
    """Test que el runbook tiene contenido significativo."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    assert len(content.strip()) > 1000, "RUNBOOK debe tener contenido significativo"
    print(f"✅ RUNBOOK tiene {len(content)} caracteres")


def test_runbook_has_required_sections():
    """Test que el runbook tiene las secciones requeridas."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    
    required_sections = [
        "Arquitectura del Sistema",
        "Monitoreo y Métricas",
        "Gestión de Cache",
        "Manejo de Incidentes",
        "Operaciones de Rutina",
        "Troubleshooting",
        "Contactos"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    assert not missing_sections, f"Secciones faltantes: {missing_sections}"
    print(f"✅ Todas las secciones requeridas están presentes: {required_sections}")


def test_runbook_has_cache_invalidation():
    """Test que el runbook documenta invalidación de cache."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    
    cache_keywords = [
        "cache.clear()",
        "invalidate_pattern",
        "redis-cli",
        "FLUSHDB",
    ]
    
    found_keywords = [kw for kw in cache_keywords if kw in content]
    assert found_keywords, f"RUNBOOK debe documentar invalidación de cache. Encontrado: {found_keywords}"
    print(f"✅ Invalidación de cache documentada: {found_keywords}")


def test_runbook_has_monitoring_commands():
    """Test que el runbook tiene comandos de monitoreo."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    
    monitoring_commands = [
        "systemctl status",
        "curl",
        "tail -f",
        "ps aux",
        "free -h",
        "df -h",
    ]
    
    found_commands = [cmd for cmd in monitoring_commands if cmd in content]
    assert len(found_commands) >= 4, f"RUNBOOK debe tener comandos de monitoreo. Encontrado: {found_commands}"
    print(f"✅ Comandos de monitoreo documentados: {found_commands}")


def test_runbook_has_health_endpoints():
    """Test que el runbook documenta endpoints de health check."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    
    health_endpoints = [
        "/health/",
        "/health/database/",
        "/health/cache/",
    ]
    
    found_endpoints = [ep for ep in health_endpoints if ep in content]
    assert found_endpoints, f"RUNBOOK debe documentar endpoints de health. Encontrado: {found_endpoints}"
    print(f"✅ Endpoints de health documentados: {found_endpoints}")


def test_runbook_has_metrics_endpoints():
    """Test que el runbook documenta endpoints de métricas."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    
    metrics_endpoints = [
        "/api/metrics/",
        "metrics",
    ]
    
    found_endpoints = [ep for ep in metrics_endpoints if ep in content]
    assert found_endpoints, f"RUNBOOK debe documentar métricas. Encontrado: {found_endpoints}"
    print(f"✅ Métricas documentadas: {found_endpoints}")


def test_runbook_has_incident_procedures():
    """Test que el runbook tiene procedimientos de incidentes."""
    project_root = Path(__file__).parent
    runbook_path = project_root / "RUNBOOK_FINAL.md"
    
    if not runbook_path.exists():
        print("❌ RUNBOOK_FINAL.md no existe")
        return
    
    content = runbook_path.read_text(encoding='utf-8')
    
    incident_keywords = [
        "Severidad",
        "Crítico",
        "15 minutos",
        "Escalación",
        "Tiempo de Respuesta",
    ]
    
    found_keywords = [kw for kw in incident_keywords if kw in content]
    assert len(found_keywords) >= 3, f"RUNBOOK debe documentar procedimientos de incidentes. Encontrado: {found_keywords}"
    print(f"✅ Procedimientos de incidentes documentados: {found_keywords}")


if __name__ == "__main__":
    print("🧪 Ejecutando tests del RUNBOOK...")
    
    try:
        test_runbook_exists()
        test_runbook_has_content()
        test_runbook_has_required_sections()
        test_runbook_has_cache_invalidation()
        test_runbook_has_monitoring_commands()
        test_runbook_has_health_endpoints()
        test_runbook_has_metrics_endpoints()
        test_runbook_has_incident_procedures()
        
        print("\n🎉 Todos los tests del RUNBOOK pasaron exitosamente!")
        print("✅ RUNBOOK_FINAL.md está completo y bien documentado")
        
    except AssertionError as e:
        print(f"\n❌ Test falló: {e}")
        exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        exit(1)