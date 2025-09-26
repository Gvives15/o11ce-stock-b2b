#!/usr/bin/env python
"""
Script to run mutation testing with mutmut and generate reports.
Target: ≥60% mutation score for Block 4 - Catalog + Offers
"""
import os
import sys
import subprocess
import json
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=cwd,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"


def check_prerequisites():
    """Check if all prerequisites are installed."""
    print("🔍 Checking prerequisites...")
    
    # Check if mutmut is installed
    returncode, stdout, stderr = run_command("mutmut --version")
    if returncode != 0:
        print("❌ mutmut is not installed. Installing...")
        returncode, _, _ = run_command("pip install mutmut")
        if returncode != 0:
            print("❌ Failed to install mutmut")
            return False
    else:
        print(f"✅ mutmut is installed: {stdout.strip()}")
    
    # Check if tests pass before mutation
    print("🧪 Running tests to ensure they pass...")
    returncode, stdout, stderr = run_command("python manage.py test apps.catalog.tests.api")
    if returncode != 0:
        print("❌ Tests are failing. Fix tests before running mutation testing.")
        print(f"Error: {stderr}")
        return False
    else:
        print("✅ All tests are passing")
    
    return True


def run_mutation_testing():
    """Run mutation testing with mutmut."""
    print("\n🧬 Starting mutation testing...")
    
    # Clean previous results
    print("🧹 Cleaning previous mutation results...")
    run_command("mutmut results --to-json > /dev/null 2>&1 || true")
    
    # Run mutation testing
    print("🚀 Running mutmut...")
    returncode, stdout, stderr = run_command("mutmut run")
    
    if returncode != 0:
        print(f"⚠️  Mutation testing completed with issues: {stderr}")
    else:
        print("✅ Mutation testing completed successfully")
    
    return True


def generate_report():
    """Generate mutation testing report."""
    print("\n📊 Generating mutation testing report...")
    
    # Get results in JSON format
    returncode, stdout, stderr = run_command("mutmut junitxml")
    if returncode == 0:
        print("✅ JUnit XML report generated")
    
    # Get summary
    returncode, stdout, stderr = run_command("mutmut results")
    if returncode == 0:
        print("\n📈 Mutation Testing Summary:")
        print(stdout)
        
        # Parse results to calculate score
        lines = stdout.strip().split('\n')
        for line in lines:
            if 'Survived:' in line or 'Killed:' in line or 'Timeout:' in line:
                print(f"  {line}")
    
    # Try to get JSON results for detailed analysis
    returncode, json_output, stderr = run_command("mutmut results --to-json")
    if returncode == 0 and json_output:
        try:
            results = json.loads(json_output)
            total_mutants = len(results)
            killed_mutants = sum(1 for r in results if r.get('status') == 'killed')
            
            if total_mutants > 0:
                mutation_score = (killed_mutants / total_mutants) * 100
                print(f"\n🎯 Mutation Score: {mutation_score:.2f}%")
                
                target_score = 60.0
                if mutation_score >= target_score:
                    print(f"✅ Target achieved! Score {mutation_score:.2f}% >= {target_score}%")
                else:
                    print(f"❌ Target not met. Score {mutation_score:.2f}% < {target_score}%")
                    print("💡 Consider adding more tests or improving test quality")
            
        except json.JSONDecodeError:
            print("⚠️  Could not parse JSON results")
    
    return True


def show_surviving_mutants():
    """Show details of surviving mutants for improvement."""
    print("\n🔍 Analyzing surviving mutants...")
    
    returncode, stdout, stderr = run_command("mutmut show")
    if returncode == 0:
        print("📋 Surviving mutants (need better tests):")
        print(stdout)
    else:
        print("ℹ️  No detailed mutant information available")


def main():
    """Main function to run mutation testing pipeline."""
    print("🧬 Mutation Testing Pipeline for Block 4 - Catalog + Offers")
    print("=" * 60)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Run mutation testing
    if not run_mutation_testing():
        sys.exit(1)
    
    # Generate report
    generate_report()
    
    # Show surviving mutants for improvement
    show_surviving_mutants()
    
    print("\n✨ Mutation testing pipeline completed!")
    print("📁 Check mutmut.html for detailed HTML report (if generated)")
    print("🎯 Target: ≥60% mutation score")


if __name__ == "__main__":
    main()