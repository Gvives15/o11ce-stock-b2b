#!/usr/bin/env python3
"""
Script para calcular el mutation score de cosmic-ray
Usado tanto en CI como localmente para análisis de mutation testing
"""
import sys
import json
import argparse

def calculate_mutation_score(input_stream=None, threshold=80.0):
    """
    Calcula el mutation score basado en el output de cosmic-ray dump
    
    Args:
        input_stream: Stream de entrada (por defecto stdin)
        threshold: Umbral mínimo para considerar el score como exitoso
        
    Returns:
        dict: Diccionario con los resultados del análisis
    """
    if input_stream is None:
        input_stream = sys.stdin
        
    killed = 0
    survived = 0
    incompetent = 0
    timeout = 0
    total = 0
    
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        
        try:
            # cosmic-ray dump devuelve listas de [work_item, work_result]
            item = json.loads(line)
            if isinstance(item, list) and len(item) == 2:
                work_item, work_result = item
                
                # Verificar que tenemos un resultado válido
                if isinstance(work_result, dict) and 'test_outcome' in work_result:
                    total += 1
                    outcome = work_result['test_outcome']
                    
                    if outcome == 'killed':
                        killed += 1
                    elif outcome == 'survived':
                        survived += 1
                    elif outcome == 'incompetent':
                        incompetent += 1
                    elif outcome == 'timeout':
                        timeout += 1
                        
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    # Calcular mutation score
    if total > 0:
        mutation_score = (killed / total) * 100
    else:
        mutation_score = 0.0
    
    return {
        'total': total,
        'killed': killed,
        'survived': survived,
        'incompetent': incompetent,
        'timeout': timeout,
        'score': mutation_score,
        'passed': mutation_score >= threshold,
        'threshold': threshold
    }

def print_results(results, format_type='detailed'):
    """
    Imprime los resultados del mutation testing
    
    Args:
        results: Diccionario con los resultados
        format_type: 'detailed', 'summary', o 'score_only'
    """
    if format_type == 'score_only':
        print(f"{results['score']:.1f}")
        return
    
    if format_type == 'summary':
        print(f"Mutation Score: {results['score']:.1f}% ({results['killed']}/{results['total']})")
        if results['passed']:
            print("✅ PASS")
        else:
            print("❌ FAIL")
        return
    
    # Formato detallado
    print("Mutation Testing Results:")
    print("========================")
    print(f"Total mutations: {results['total']}")
    print(f"Killed: {results['killed']}")
    print(f"Survived: {results['survived']}")
    print(f"Incompetent: {results['incompetent']}")
    print(f"Timeout: {results['timeout']}")
    print()
    print(f"Mutation Score: {results['score']:.1f}%")
    
    if results['passed']:
        print(f"✅ Good mutation score (>= {results['threshold']}%)")
    else:
        print(f"❌ Low mutation score - tests need improvement")
        print(f"   Target: >= {results['threshold']}%")

def main():
    parser = argparse.ArgumentParser(description='Calculate mutation testing score from cosmic-ray dump')
    parser.add_argument('--threshold', type=float, default=80.0,
                       help='Minimum score threshold (default: 80.0)')
    parser.add_argument('--format', choices=['detailed', 'summary', 'score_only'],
                       default='detailed', help='Output format')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if score below threshold')
    
    args = parser.parse_args()
    
    results = calculate_mutation_score(threshold=args.threshold)
    print_results(results, args.format)
    
    if args.exit_code and not results['passed']:
        sys.exit(1)

if __name__ == "__main__":
    main()