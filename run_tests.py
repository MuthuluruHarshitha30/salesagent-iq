"""
Test Runner for Mini AI Business Intelligence Assistant.
Runs all test modules with verbose output.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(BASE_DIR / "tests"), pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print("=" * 60)

    if result.wasSuccessful():
        print("ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
        return 0
    else:
        print("SOME TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
