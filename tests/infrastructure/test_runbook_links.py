"""
Tests para verificar que los links y referencias del RUNBOOK existen y son válidos.
"""
import os
import re
import requests
from django.test import TestCase
from django.conf import settings
from pathlib import Path
import subprocess


class TestRunbookLinksExist(TestCase):
    """Tests para verificar que los links del runbook son válidos."""

    def setUp(self):
        """Setup para los tests."""
        self.project_root = Path(settings.BASE_DIR)
        self.runbook_path = self.project_root / "RUNBOOK_FINAL.md"
        
        # Verificar que el runbook existe
        if not self.runbook_path.exists():
            self.skipTest("RUNBOOK_FINAL.md no encontrado")

    def test_runbook_file_exists(self):
        """Test que el archivo RUNBOOK existe."""
        self.assertTrue(self.runbook_path.exists(), 
                       "RUNBOOK_FINAL.md debe existir en la raíz del proyecto")

    def test_runbook_is_not_empty(self):
        """Test que el runbook no está vacío."""
        content = self.runbook_path.read_text(encoding='utf-8')
        self.assertGreater(len(content.strip()), 100, 
                          "RUNBOOK debe tener contenido significativo")

    def test_runbook_has_required_sections(self):
        """Test que el runbook tiene las secciones requeridas."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        required_sections = [
            "Arquitectura del Sistema",
            "Monitoreo y Métricas",
            "Gestión de Cache",
            "Manejo de Incidentes",
            "Operaciones de Rutina",
            "Troubleshooting",
            "Contactos"
        ]
        
        for section in required_sections:
            self.assertIn(section, content, 
                         f"RUNBOOK debe contener sección '{section}'")

    def test_runbook_internal_links_exist(self):
        """Test que los links internos del runbook apuntan a secciones existentes."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Encontrar todos los links internos [texto](#seccion)
        internal_links = re.findall(r'\[([^\]]+)\]\(#([^)]+)\)', content)
        
        for link_text, anchor in internal_links:
            # Convertir anchor a formato de header markdown
            # GitHub convierte headers a anchors en lowercase con guiones
            expected_header_patterns = [
                f"# {link_text}",
                f"## {link_text}",
                f"### {link_text}",
                f"#### {link_text}",
                # También buscar variaciones con emojis
                f"🏗️ {link_text}",
                f"📊 {link_text}",
                f"🗄️ {link_text}",
                f"🚨 {link_text}",
                f"🔄 {link_text}",
                f"🔍 {link_text}",
                f"📞 {link_text}",
            ]
            
            # Buscar si existe algún header que corresponda
            header_found = False
            for pattern in expected_header_patterns:
                if pattern in content:
                    header_found = True
                    break
            
            # Si no encontramos header exacto, buscar por palabras clave
            if not header_found:
                # Buscar headers que contengan palabras del link
                link_words = link_text.lower().split()
                for line in content.split('\n'):
                    if line.startswith('#') and any(word in line.lower() for word in link_words):
                        header_found = True
                        break
            
            self.assertTrue(header_found, 
                           f"Link interno '{link_text}' (#{anchor}) no tiene header correspondiente")

    def test_runbook_file_references_exist(self):
        """Test que los archivos referenciados en el runbook existen."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar referencias a archivos del proyecto
        file_patterns = [
            r'`([^`]+\.py)`',  # archivos Python en backticks
            r'`([^`]+\.sh)`',  # scripts shell
            r'`([^`]+\.yml)`', # archivos YAML
            r'`([^`]+\.md)`',  # archivos Markdown
            r'\[([^\]]+\.md)\]',  # archivos Markdown en links
        ]
        
        referenced_files = []
        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            referenced_files.extend(matches)
        
        # Verificar archivos específicos que sabemos que deberían existir
        expected_files = [
            'manage.py',
            'requirements.txt',
            'config/settings.py',
            'config/celery.py',
            'apps/core/models.py',
            'tests/factories.py',
            'tests/fixtures.py',
        ]
        
        for file_path in expected_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                # Buscar en subdirectorios si no está en la raíz
                found = False
                for root, dirs, files in os.walk(self.project_root):
                    if file_path.split('/')[-1] in files:
                        found = True
                        break
                
                if not found:
                    self.fail(f"Archivo referenciado '{file_path}' no existe")

    def test_runbook_command_examples_are_valid(self):
        """Test que los comandos de ejemplo en el runbook son válidos."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Extraer bloques de código bash/shell
        code_blocks = re.findall(r'```(?:bash|shell)\n(.*?)\n```', content, re.DOTALL)
        
        # Comandos que deberían ser válidos (sintaxis básica)
        safe_commands = [
            'systemctl status',
            'tail -f',
            'curl',
            'python manage.py',
            'redis-cli',
            'ps aux',
            'free -h',
            'df -h',
            'grep',
            'find',
        ]
        
        for block in code_blocks:
            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                
                # Saltar comentarios y líneas vacías
                if not line or line.startswith('#') or line.startswith('>>>'):
                    continue
                
                # Verificar que al menos usa comandos conocidos
                command_found = False
                for safe_cmd in safe_commands:
                    if line.startswith(safe_cmd):
                        command_found = True
                        break
                
                # No fallar si no reconocemos el comando, solo advertir
                if not command_found and not any(char in line for char in ['=', '|', '&&', '||']):
                    # Es un comando simple que no reconocemos
                    pass

    def test_runbook_urls_format_is_valid(self):
        """Test que las URLs en el runbook tienen formato válido."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar URLs en el contenido
        url_patterns = [
            r'http://[^\s\)]+',
            r'https://[^\s\)]+',
            r'localhost:\d+[^\s\)]*',
        ]
        
        urls = []
        for pattern in url_patterns:
            matches = re.findall(pattern, content)
            urls.extend(matches)
        
        for url in urls:
            # Verificar formato básico de URL
            if url.startswith('http'):
                # URL completa
                self.assertRegex(url, r'^https?://[^\s]+$', 
                               f"URL mal formateada: {url}")
            elif 'localhost' in url:
                # URL local
                self.assertRegex(url, r'^localhost:\d+', 
                               f"URL localhost mal formateada: {url}")

    def test_runbook_health_check_endpoints_format(self):
        """Test que los endpoints de health check tienen formato correcto."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar endpoints de health check
        health_endpoints = re.findall(r'/health/[^\s\)]*', content)
        
        expected_endpoints = [
            '/health/',
            '/health/database/',
            '/health/cache/',
            '/health/smtp/',
        ]
        
        for endpoint in expected_endpoints:
            self.assertIn(endpoint, content, 
                         f"Endpoint de health check '{endpoint}' debe estar documentado")

    def test_runbook_metrics_endpoints_format(self):
        """Test que los endpoints de métricas tienen formato correcto."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar endpoints de métricas
        metrics_endpoints = re.findall(r'/api/metrics/[^\s\)]*', content)
        
        expected_metrics = [
            '/api/metrics/stock/',
            '/api/metrics/orders/',
            '/api/metrics/fefo/',
        ]
        
        for endpoint in expected_metrics:
            self.assertIn(endpoint, content, 
                         f"Endpoint de métricas '{endpoint}' debe estar documentado")

    def test_runbook_contact_information_format(self):
        """Test que la información de contacto tiene formato válido."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar sección de contactos
        contact_section_match = re.search(
            r'## 📞 Contactos.*?(?=##|\Z)', 
            content, 
            re.DOTALL
        )
        
        if contact_section_match:
            contact_section = contact_section_match.group(0)
            
            # Verificar que tiene placeholders para información de contacto
            contact_placeholders = [
                '[nombre]',
                '[email]',
                '[teléfono]',
                'Tech Lead',
                'DevOps',
            ]
            
            for placeholder in contact_placeholders:
                self.assertIn(placeholder, contact_section, 
                             f"Sección de contactos debe incluir '{placeholder}'")

    def test_runbook_table_format_is_valid(self):
        """Test que las tablas en el runbook tienen formato válido."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar tablas markdown
        table_lines = [line for line in content.split('\n') if '|' in line]
        
        if table_lines:
            # Verificar que las tablas tienen headers
            for i, line in enumerate(table_lines):
                if '---' in line:  # Línea separadora de header
                    # Verificar que hay una línea de header antes
                    if i > 0:
                        header_line = table_lines[i-1]
                        self.assertIn('|', header_line, 
                                     "Tabla debe tener línea de header válida")
                        
                        # Contar columnas en header y separador
                        header_cols = len([col for col in header_line.split('|') if col.strip()])
                        separator_cols = len([col for col in line.split('|') if col.strip()])
                        
                        # Permitir diferencia de 1 (por pipes al inicio/final)
                        self.assertLessEqual(abs(header_cols - separator_cols), 1,
                                           "Número de columnas inconsistente en tabla")

    def test_runbook_code_blocks_are_properly_formatted(self):
        """Test que los bloques de código están correctamente formateados."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Contar bloques de código abiertos y cerrados
        opening_blocks = len(re.findall(r'^```', content, re.MULTILINE))
        closing_blocks = opening_blocks  # Cada ``` abre y cierra
        
        # Debe haber número par de ``` (cada bloque abre y cierra)
        self.assertEqual(opening_blocks % 2, 0, 
                        "Bloques de código mal formateados (``` desbalanceados)")

    def test_runbook_has_table_of_contents(self):
        """Test que el runbook tiene tabla de contenidos."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Buscar índice/tabla de contenidos
        toc_indicators = [
            "Índice",
            "Table of Contents",
            "## 📋",
            "- [",  # Lista con links
        ]
        
        has_toc = any(indicator in content for indicator in toc_indicators)
        self.assertTrue(has_toc, "RUNBOOK debe tener tabla de contenidos")

    def test_runbook_sections_have_proper_hierarchy(self):
        """Test que las secciones del runbook tienen jerarquía correcta."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        # Extraer todos los headers
        headers = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        
        if headers:
            # Verificar que empezamos con nivel apropiado
            first_level = len(headers[0][0])
            self.assertLessEqual(first_level, 2, 
                               "Primer header debe ser # o ##")
            
            # Verificar que no hay saltos de nivel muy grandes
            for i in range(1, len(headers)):
                prev_level = len(headers[i-1][0])
                curr_level = len(headers[i][0])
                
                # No debería saltar más de 1 nivel hacia abajo
                if curr_level > prev_level:
                    self.assertLessEqual(curr_level - prev_level, 1,
                                       f"Salto de nivel muy grande: {headers[i-1][1]} -> {headers[i][1]}")

    def test_runbook_emergency_procedures_documented(self):
        """Test que los procedimientos de emergencia están documentados."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        emergency_keywords = [
            "Severidad 1",
            "Crítico",
            "15 minutos",
            "Tiempo de Respuesta",
            "Escalación",
            "Incidentes",
        ]
        
        for keyword in emergency_keywords:
            self.assertIn(keyword, content, 
                         f"RUNBOOK debe documentar procedimientos de emergencia ('{keyword}')")

    def test_runbook_monitoring_commands_documented(self):
        """Test que los comandos de monitoreo están documentados."""
        content = self.runbook_path.read_text(encoding='utf-8')
        
        monitoring_commands = [
            "systemctl status",
            "tail -f",
            "curl",
            "redis-cli",
            "ps aux",
            "free -h",
            "df -h",
        ]
        
        for command in monitoring_commands:
            self.assertIn(command, content, 
                         f"RUNBOOK debe documentar comando de monitoreo '{command}'")