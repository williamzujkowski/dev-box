#!/usr/bin/env python3
"""
Test runner script for the LLM Sandbox Vagrant Agent.

This script provides a convenient interface for running different types of tests
with appropriate configuration and reporting.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    """Test runner with support for different test categories and reporting."""

    def __init__(self):
        """Initialize test runner."""
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.coverage_dir = self.test_dir / "coverage_html"
        self.logs_dir = self.test_dir / "logs"

        # Ensure directories exist
        self.coverage_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    def run_unit_tests(self, verbose=False, coverage=True):
        """Run unit tests."""
        print("🧪 Running Unit Tests...")

        cmd = ["python", "-m", "pytest", "tests/unit/", "-m", "unit", "--timeout=30"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend(
                [
                    "--cov=src",
                    "--cov-report=html:" + str(self.coverage_dir / "unit"),
                    "--cov-report=term-missing",
                ]
            )

        return self._run_command(cmd)

    def run_integration_tests(self, verbose=False, skip_slow=False):
        """Run integration tests."""
        print("🔗 Running Integration Tests...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/integration/",
            "-m",
            "integration",
            "--timeout=300",
        ]

        if skip_slow:
            cmd.extend(["-m", "not slow"])

        if verbose:
            cmd.append("-v")

        return self._run_command(cmd)

    def run_security_tests(self, verbose=False):
        """Run security tests."""
        print("🔒 Running Security Tests...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/security/",
            "-m",
            "security",
            "--timeout=120",
        ]

        if verbose:
            cmd.append("-v")

        return self._run_command(cmd)

    def run_performance_tests(self, verbose=False, benchmark=False):
        """Run performance tests."""
        print("⚡ Running Performance Tests...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/performance/",
            "-m",
            "performance",
            "--timeout=600",
        ]

        if benchmark:
            cmd.append("--benchmark-only")

        if verbose:
            cmd.append("-v")

        return self._run_command(cmd)

    def run_all_tests(self, verbose=False, coverage=True, skip_slow=False):
        """Run all test categories."""
        print("🚀 Running All Tests...")

        results = {
            "unit": self.run_unit_tests(verbose, coverage),
            "integration": self.run_integration_tests(verbose, skip_slow),
            "security": self.run_security_tests(verbose),
            "performance": self.run_performance_tests(verbose),
        }

        return all(results.values())

    def run_quick_tests(self, verbose=False):
        """Run quick tests (unit + fast integration)."""
        print("⚡ Running Quick Tests...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "tests/integration/",
            "-m",
            "unit or (integration and not slow)",
            "--timeout=60",
        ]

        if verbose:
            cmd.append("-v")

        return self._run_command(cmd)

    def run_smoke_tests(self, verbose=False):
        """Run smoke tests for basic functionality."""
        print("💨 Running Smoke Tests...")

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/",
            "-k",
            "test_basic or test_smoke or test_sanity",
            "--timeout=30",
        ]

        if verbose:
            cmd.append("-v")

        return self._run_command(cmd)

    def run_tests_by_pattern(self, pattern, verbose=False):
        """Run tests matching a specific pattern."""
        print(f"🔍 Running Tests Matching: {pattern}")

        cmd = ["python", "-m", "pytest", "tests/", "-k", pattern]

        if verbose:
            cmd.append("-v")

        return self._run_command(cmd)

    def run_coverage_report(self):
        """Generate comprehensive coverage report."""
        print("📊 Generating Coverage Report...")

        # Run tests with coverage
        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/unit/",
            "tests/integration/",
            "-m",
            "not slow",
            "--cov=src",
            "--cov-report=html:" + str(self.coverage_dir),
            "--cov-report=term-missing",
            "--cov-report=json:" + str(self.logs_dir / "coverage.json"),
        ]

        return self._run_command(cmd)

    def run_linting(self):
        """Run code linting and formatting checks."""
        print("🔍 Running Code Quality Checks...")

        commands = [
            ["python", "-m", "flake8", "src/", "tests/"],
            ["python", "-m", "black", "--check", "src/", "tests/"],
            ["python", "-m", "isort", "--check-only", "src/", "tests/"],
            ["python", "-m", "mypy", "src/"],
            ["python", "-m", "bandit", "-r", "src/", "-ll"],
        ]

        results = []
        for cmd in commands:
            print(f"Running: {' '.join(cmd)}")
            result = self._run_command(cmd, check=False)
            results.append(result)

        return all(results)

    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("📋 Generating Test Report...")

        report_file = self.logs_dir / "test_report.json"

        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/",
            "--json-report",
            f"--json-report-file={report_file}",
            "--html=" + str(self.logs_dir / "test_report.html"),
            "--self-contained-html",
        ]

        result = self._run_command(cmd)

        if result and report_file.exists():
            self._print_test_summary(report_file)

        return result

    def _run_command(self, cmd, check=True):
        """Run a command and return success status."""
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)

            result = subprocess.run(
                cmd, cwd=self.project_root, env=env, check=check, capture_output=False
            )

            return result.returncode == 0

        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed with exit code {e.returncode}")
            return False
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return False

    def _print_test_summary(self, report_file):
        """Print test summary from JSON report."""
        try:
            with open(report_file) as f:
                report = json.load(f)

            summary = report.get("summary", {})

            print("\n📊 Test Summary:")
            print(f"  Total Tests: {summary.get('total', 0)}")
            print(f"  Passed: {summary.get('passed', 0)} ✅")
            print(f"  Failed: {summary.get('failed', 0)} ❌")
            print(f"  Skipped: {summary.get('skipped', 0)} ⏭️")
            print(f"  Duration: {summary.get('duration', 0):.2f}s")

            if summary.get("failed", 0) > 0:
                print("\n❌ Failed Tests:")
                for test in report.get("tests", []):
                    if test.get("outcome") == "failed":
                        print(f"  - {test.get('nodeid', 'Unknown')}")

        except Exception as e:
            print(f"❌ Error reading test report: {e}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Test runner for LLM Sandbox Vagrant Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py unit              # Run unit tests
  python run_tests.py integration       # Run integration tests
  python run_tests.py security          # Run security tests
  python run_tests.py performance       # Run performance tests
  python run_tests.py all               # Run all tests
  python run_tests.py quick             # Run quick tests
  python run_tests.py smoke             # Run smoke tests
  python run_tests.py coverage          # Generate coverage report
  python run_tests.py lint              # Run linting
  python run_tests.py report            # Generate test report
  python run_tests.py pattern "vm_*"    # Run tests matching pattern
        """,
    )

    parser.add_argument(
        "test_type",
        choices=[
            "unit",
            "integration",
            "security",
            "performance",
            "all",
            "quick",
            "smoke",
            "coverage",
            "lint",
            "report",
            "pattern",
        ],
        help="Type of tests to run",
    )

    parser.add_argument(
        "pattern", nargs="?", help="Test pattern (for 'pattern' test type)"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument(
        "--no-coverage", action="store_true", help="Skip coverage reporting"
    )

    parser.add_argument("--skip-slow", action="store_true", help="Skip slow tests")

    parser.add_argument(
        "--benchmark", action="store_true", help="Run benchmark tests only"
    )

    args = parser.parse_args()

    runner = TestRunner()

    start_time = time.time()

    # Run the requested tests
    if args.test_type == "unit":
        success = runner.run_unit_tests(args.verbose, not args.no_coverage)
    elif args.test_type == "integration":
        success = runner.run_integration_tests(args.verbose, args.skip_slow)
    elif args.test_type == "security":
        success = runner.run_security_tests(args.verbose)
    elif args.test_type == "performance":
        success = runner.run_performance_tests(args.verbose, args.benchmark)
    elif args.test_type == "all":
        success = runner.run_all_tests(
            args.verbose, not args.no_coverage, args.skip_slow
        )
    elif args.test_type == "quick":
        success = runner.run_quick_tests(args.verbose)
    elif args.test_type == "smoke":
        success = runner.run_smoke_tests(args.verbose)
    elif args.test_type == "coverage":
        success = runner.run_coverage_report()
    elif args.test_type == "lint":
        success = runner.run_linting()
    elif args.test_type == "report":
        success = runner.generate_test_report()
    elif args.test_type == "pattern":
        if not args.pattern:
            print("❌ Pattern required for 'pattern' test type")
            sys.exit(1)
        success = runner.run_tests_by_pattern(args.pattern, args.verbose)
    else:
        print(f"❌ Unknown test type: {args.test_type}")
        sys.exit(1)

    end_time = time.time()
    duration = end_time - start_time

    print(f"\n⏱️  Total execution time: {duration:.2f}s")

    if success:
        print("✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
