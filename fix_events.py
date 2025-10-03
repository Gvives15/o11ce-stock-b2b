#!/usr/bin/env python3
"""
Script para corregir automáticamente las clases de eventos con problemas de dataclass.
"""

import re
import os

def fix_events_file():
    """Corrige el archivo de eventos reemplazando las clases problemáticas"""
    
    events_file = r"C:\Users\germa\OneDrive\Documentos\Programas\BFF\apps\stock\events.py"
    
    # Leer el archivo
    with open(events_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrones para corregir
    patterns = [
        # Patrón para campos sin valores por defecto que siguen a campos con valores por defecto
        (r'(\s+)(\w+): (str|int|Decimal|date|bool)(\s*\n)', r'\1\2: \3 = field(default="")\4'),
        (r'(\s+)(\w+): Optional\[(.*?)\](\s*\n)', r'\1\2: Optional[\3] = field(default=None)\4'),
        (r'(\s+)(\w+): Decimal = field\(default=""\)', r'\1\2: Decimal = field(default=Decimal("0"))'),
        (r'(\s+)(\w+): int = field\(default=""\)', r'\1\2: int = field(default=0)'),
        (r'(\s+)(\w+): bool = field\(default=""\)', r'\1\2: bool = field(default=False)'),
        (r'(\s+)(\w+): date = field\(default=""\)', r'\1\2: Optional[date] = field(default=None)'),
    ]
    
    # Aplicar correcciones
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Escribir el archivo corregido
    with open(events_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Archivo de eventos corregido exitosamente")

if __name__ == "__main__":
    fix_events_file()