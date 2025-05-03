#!/usr/bin/env python3
"""
MERL-T Test Runner

This script provides a convenient way to run all tests or specific test suites.
"""

import argparse
import os
import sys
import pytest


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    args = ["merl_t/tests/unit"]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=merl_t", "--cov-report=term", "--cov-report=html"])
    
    return pytest.main(args)


def run_integration_tests(verbose=False, coverage=False):
    """Run integration tests."""
    args = ["merl_t/tests/integration", "-m", "integration"]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=merl_t", "--cov-report=term", "--cov-report=html"])
    
    return pytest.main(args)


def run_all_tests(verbose=False, coverage=False):
    """Run all tests."""
    args = ["merl_t/tests"]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=merl_t", "--cov-report=term", "--cov-report=html"])
    
    return pytest.main(args)


def run_specific_test(test_path, verbose=False, coverage=False):
    """Run a specific test file or directory."""
    if not os.path.exists(test_path):
        print(f"Error: Test path '{test_path}' does not exist")
        return 1
    
    args = [test_path]
    
    if verbose:
        args.append("-v")
    
    if coverage:
        args.extend(["--cov=merl_t", "--cov-report=term", "--cov-report=html"])
    
    return pytest.main(args)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run MERL-T tests")
    
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--path",
        help="Path to a specific test file or directory to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate a coverage report"
    )
    
    args = parser.parse_args()
    
    if args.path:
        return run_specific_test(args.path, verbose=args.verbose, coverage=args.coverage)
    
    if args.type == "unit":
        return run_unit_tests(verbose=args.verbose, coverage=args.coverage)
    elif args.type == "integration":
        return run_integration_tests(verbose=args.verbose, coverage=args.coverage)
    else:  # all
        return run_all_tests(verbose=args.verbose, coverage=args.coverage)


if __name__ == "__main__":
    sys.exit(main()) 