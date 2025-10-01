#!/usr/bin/env python3
"""
Mutation Testing para Windows - Enfoque en funciones críticas de pricing
Alternativa a mutmut para alcanzar ≥60% mutation score en Block 4.
"""

import os
import sys
import ast
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from decimal import Decimal
import json


@dataclass
class MutationResult:
    """Resultado de una mutación específica."""
    mutation_id: str
    file_path: str
    line_number: int
    original_code: str
    mutated_code: str
    test_passed: bool
    error_message: str = ""


@dataclass
class MutationReport:
    """Reporte completo de mutation testing."""
    total_mutations: int
    killed_mutations: int
    survived_mutations: int
    mutation_score: float
    results: List[MutationResult]


class PricingMutationTester:
    """
    Mutation tester específico para funciones críticas de pricing.
    Enfocado en apply_discount() y calculate_final_price().
    """
    
    def __init__(self, target_file: str = "apps/catalog/utils.py"):
        self.target_file = Path(target_file)
        self.test_command = "python manage.py test apps.catalog.tests.api.test_products_pricing --verbosity=0"
        self.mutations = []
        
    def generate_mutations(self) -> List[Dict[str, Any]]:
        """
        Genera mutaciones específicas para las funciones críticas de pricing.
        """
        mutations = []
        
        # Mutaciones para apply_discount()
        apply_discount_mutations = [
            # Operadores aritméticos
            {"line_contains": "price * (value_pct / 100)", "original": "*", "mutated": "+", "type": "arithmetic"},
            {"line_contains": "price * (value_pct / 100)", "original": "/", "mutated": "*", "type": "arithmetic"},
            {"line_contains": "price - discount_amount", "original": "-", "mutated": "+", "type": "arithmetic"},
            
            # Operadores de comparación
            {"line_contains": "price <= 0", "original": "<=", "mutated": "<", "type": "comparison"},
            {"line_contains": "price <= 0", "original": "<=", "mutated": "==", "type": "comparison"},
            {"line_contains": "value_pct < 0", "original": "<", "mutated": "<=", "type": "comparison"},
            {"line_contains": "value_pct > 100", "original": ">", "mutated": ">=", "type": "comparison"},
            
            # Constantes numéricas
            {"line_contains": "value_pct / 100", "original": "100", "mutated": "10", "type": "constant"},
            {"line_contains": "value_pct / 100", "original": "100", "mutated": "1000", "type": "constant"},
            
            # Valores de retorno
            {"line_contains": "return discounted_price.quantize", "original": "discounted_price", "mutated": "price", "type": "return"},
        ]
        
        # Mutaciones para calculate_final_price()
        calculate_final_price_mutations = [
            # Condiciones lógicas
            {"line_contains": "if not segment:", "original": "not", "mutated": "", "type": "logical"},
            {"line_contains": "if not discount_benefits.exists():", "original": "not", "mutated": "", "type": "logical"},
            
            # Filtros y ordenamiento
            {"line_contains": 'filter(type="discount")', "original": '"discount"', "mutated": '"benefit"', "type": "string"},
            {"line_contains": "order_by('-value')", "original": "'-value'", "mutated": "'value'", "type": "string"},
            
            # Valores de retorno
            {"line_contains": "return product.price", "original": "product.price", "mutated": "Decimal('0')", "type": "return"},
            {"line_contains": "return apply_discount", "original": "apply_discount(product.price, best_benefit.value)", "mutated": "product.price", "type": "return"},
        ]
        
        mutations.extend(apply_discount_mutations)
        mutations.extend(calculate_final_price_mutations)
        
        return mutations
    
    def apply_mutation(self, original_content: str, mutation: Dict[str, Any]) -> Tuple[str, int]:
        """
        Aplica una mutación específica al contenido del archivo.
        """
        lines = original_content.split('\n')
        mutated_content = original_content
        line_number = -1
        
        for i, line in enumerate(lines):
            if mutation["line_contains"] in line and mutation["original"] in line:
                # Aplicar la mutación
                mutated_line = line.replace(mutation["original"], mutation["mutated"], 1)
                lines[i] = mutated_line
                mutated_content = '\n'.join(lines)
                line_number = i + 1
                break
                
        return mutated_content, line_number
    
    def run_tests(self) -> bool:
        """
        Ejecuta los tests y retorna True si pasan, False si fallan.
        """
        try:
            # Usar shell=True en Windows para mejor compatibilidad
            result = subprocess.run(
                self.test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path.cwd()
            )
            print(f"    Test exit code: {result.returncode}")
            if result.returncode != 0:
                print(f"    Test stderr: {result.stderr[:200]}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("    Test timeout")
            return False
        except Exception as e:
            print(f"    Test exception: {e}")
            return False
    
    def run_mutation_testing(self) -> MutationReport:
        """
        Ejecuta el mutation testing completo.
        """
        print("🧬 Iniciando Mutation Testing para funciones críticas de pricing...")
        
        # Leer archivo original
        with open(self.target_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Backup del archivo original
        backup_path = self.target_file.with_suffix('.py.backup')
        shutil.copy2(self.target_file, backup_path)
        
        mutations = self.generate_mutations()
        results = []
        
        try:
            # Verificar que los tests pasan con código original
            print("✅ Verificando tests con código original...")
            if not self.run_tests():
                print("❌ Los tests fallan con el código original. Abortando.")
                return MutationReport(0, 0, 0, 0.0, [])
            
            print(f"🎯 Aplicando {len(mutations)} mutaciones...")
            
            for i, mutation in enumerate(mutations):
                print(f"  Mutación {i+1}/{len(mutations)}: {mutation['type']} - {mutation['original']} → {mutation['mutated']}")
                
                # Aplicar mutación
                mutated_content, line_number = self.apply_mutation(original_content, mutation)
                
                if line_number == -1:
                    print(f"    ⚠️  No se encontró el patrón: {mutation['line_contains']}")
                    continue
                
                # Escribir archivo mutado
                with open(self.target_file, 'w', encoding='utf-8') as f:
                    f.write(mutated_content)
                
                # Ejecutar tests
                test_passed = self.run_tests()
                
                # Crear resultado
                mutation_result = MutationResult(
                    mutation_id=f"mut_{i+1}",
                    file_path=str(self.target_file),
                    line_number=line_number,
                    original_code=mutation["original"],
                    mutated_code=mutation["mutated"],
                    test_passed=test_passed
                )
                
                results.append(mutation_result)
                
                if test_passed:
                    print(f"    🟡 SURVIVED - Los tests pasaron con la mutación")
                else:
                    print(f"    🔴 KILLED - Los tests detectaron la mutación")
                
                # Restaurar archivo original para siguiente mutación
                with open(self.target_file, 'w', encoding='utf-8') as f:
                    f.write(original_content)
        
        finally:
            # Restaurar archivo original
            shutil.copy2(backup_path, self.target_file)
            backup_path.unlink()
        
        # Calcular estadísticas
        killed = sum(1 for r in results if not r.test_passed)
        survived = sum(1 for r in results if r.test_passed)
        total = len(results)
        mutation_score = (killed / total * 100) if total > 0 else 0
        
        return MutationReport(
            total_mutations=total,
            killed_mutations=killed,
            survived_mutations=survived,
            mutation_score=mutation_score,
            results=results
        )
    
    def generate_report(self, report: MutationReport) -> str:
        """
        Genera un reporte detallado del mutation testing.
        """
        report_lines = [
            "=" * 80,
            "🧬 MUTATION TESTING REPORT - BLOCK 4 PRICING FUNCTIONS",
            "=" * 80,
            "",
            f"📊 RESUMEN:",
            f"  • Total de mutaciones: {report.total_mutations}",
            f"  • Mutaciones eliminadas (KILLED): {report.killed_mutations}",
            f"  • Mutaciones supervivientes (SURVIVED): {report.survived_mutations}",
            f"  • Mutation Score: {report.mutation_score:.1f}%",
            "",
            f"🎯 OBJETIVO: ≥60% mutation score",
            f"📈 RESULTADO: {'✅ ALCANZADO' if report.mutation_score >= 60 else '❌ NO ALCANZADO'}",
            "",
            "📋 DETALLE DE MUTACIONES:",
            ""
        ]
        
        for result in report.results:
            status = "🔴 KILLED" if not result.test_passed else "🟡 SURVIVED"
            report_lines.append(
                f"  {status} | Línea {result.line_number} | "
                f"{result.original_code} → {result.mutated_code}"
            )
        
        if report.survived_mutations > 0:
            report_lines.extend([
                "",
                "⚠️  MUTACIONES SUPERVIVIENTES (requieren atención):",
                ""
            ])
            
            for result in report.results:
                if result.test_passed:
                    report_lines.append(
                        f"  • Línea {result.line_number}: {result.original_code} → {result.mutated_code}"
                    )
        
        report_lines.extend([
            "",
            "💡 RECOMENDACIONES:",
            "  • Agregar tests para cubrir mutaciones supervivientes",
            "  • Revisar edge cases en funciones de pricing",
            "  • Considerar property-based testing adicional",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


def main():
    """Función principal para ejecutar mutation testing."""
    tester = PricingMutationTester()
    
    print("🚀 Iniciando Mutation Testing para Block 4 - Catalog + Offers")
    print("🎯 Objetivo: Alcanzar ≥60% mutation score en funciones críticas")
    print()
    
    report = tester.run_mutation_testing()
    
    # Generar y mostrar reporte
    report_text = tester.generate_report(report)
    print(report_text)
    
    # Guardar reporte en archivo
    report_file = Path("mutation_testing_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"📄 Reporte guardado en: {report_file}")
    
    # Guardar datos JSON para análisis posterior
    json_report = {
        "mutation_score": report.mutation_score,
        "total_mutations": report.total_mutations,
        "killed_mutations": report.killed_mutations,
        "survived_mutations": report.survived_mutations,
        "target_achieved": report.mutation_score >= 60,
        "results": [
            {
                "mutation_id": r.mutation_id,
                "line_number": r.line_number,
                "original_code": r.original_code,
                "mutated_code": r.mutated_code,
                "killed": not r.test_passed
            }
            for r in report.results
        ]
    }
    
    json_file = Path("mutation_testing_data.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Datos JSON guardados en: {json_file}")
    
    return report.mutation_score >= 60


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)