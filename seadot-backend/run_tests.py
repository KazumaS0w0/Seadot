"""
Seadot Test Runner Script
===========================
Run all unit and integration tests for Seadot Backend.

Usage in Windows CMD/PowerShell:
    cd seadot-backend
    venv\Scripts\activate
    python run_tests.py

Or run specific test types:
    python run_tests.py --unit    # Run only unit tests
    python run_tests.py --api     # Run only API integration tests
    python run_tests.py --all     # Run all tests (default)
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_test_suite(test_type: str = "all"):
    """
    Run the test suite based on test type
    
    Args:
        test_type: "all", "unit", or "api"
    """
    
    # Change to project directory
    script_dir = Path(__file__).parent.absolute()
    subprocess.run(
        ["cmd", "/c", "cd", str(script_dir)],
        shell=True,
        check=True
    )
    
    print(f"\n{'='*60}")
    print(f"SEADOT BACKEND TEST RUNNER")
    print(f"Test Type: {test_type.upper()}")
    print(f"{'='*60}\n")
    
    if test_type == "all":
        # Run unit tests first
        print("\n>>> Running Unit Tests...")
        print("-" * 40)
        result = subprocess.run(
            ["python", "-m", "pytest", 
             "tests/unit/", 
             "-v", "--tb=short"],
            cwd=str(script_dir),
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
        # Run API integration tests
        print("\n>>> Running API Integration Tests...")
        print("-" * 40)
        result = subprocess.run(
            ["python", "-m", "pytest", 
             "tests/integration/", 
             "-v", "--tb=short"],
            cwd=str(script_dir),
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
    elif test_type == "unit":
        print("\n>>> Running Unit Tests Only...")
        print("-" * 40)
        result = subprocess.run(
            ["python", "-m", "pytest", 
             "tests/unit/", 
             "-v", "--tb=short"],
            cwd=str(script_dir),
            capture_output=True,
            text=True
        )
        print(result.stdout)
        
    elif test_type == "api":
        print("\n>>> Running API Integration Tests Only...")
        print("-" * 40)
        result = subprocess.run(
            ["python", "-m", "pytest", 
             "tests/integration/", 
             "-v", "--tb=short"],
            cwd=str(script_dir),
            capture_output=True,
            text=True
        )
        print(result.stdout)
    
    # Return exit code
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Seadot Backend Tests")
    parser.add_argument(
        "--unit", 
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--api", 
        action="store_true",
        help="Run only API integration tests"
    )
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Run all tests (default)"
    )
    
    args = parser.parse_args()
    
    # Determine test type from arguments
    if args.unit:
        test_type = "unit"
    elif args.api:
        test_type = "api"
    else:
        test_type = "all"
    
    exit_code = run_test_suite(test_type)
    
    print(f"\n{'='*60}")
    if exit_code == 0:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print(f"{'='*60}\n")
    
    sys.exit(exit_code)
