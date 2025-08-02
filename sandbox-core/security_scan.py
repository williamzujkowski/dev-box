#!/usr/bin/env python3
"""
Security scanning script for the sandbox-core project.

This script runs security scans using bandit and other security tools
to detect potential vulnerabilities in the codebase.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from typing import Dict


class SecurityScanner:
    """Security scanner for Python code."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.results: Dict[str, Any] = {}

    def run_bandit_scan(self) -> Dict[str, Any]:
        """Run bandit security scanner."""
        print("🔍 Running bandit security scan...")

        try:
            # Run bandit with JSON output
            result = subprocess.run(
                [
                    "bandit",
                    "-r",
                    str(self.src_dir),
                    "-f",
                    "json",
                    "-o",
                    str(self.project_root / "bandit-report.json"),
                    "--severity-level",
                    "medium",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # Load the JSON report
            report_file = self.project_root / "bandit-report.json"
            if report_file.exists():
                with open(report_file) as f:
                    report = json.load(f)

                return {
                    "tool": "bandit",
                    "success": True,
                    "issues_found": len(report.get("results", [])),
                    "high_severity": len(
                        [
                            r
                            for r in report.get("results", [])
                            if r.get("issue_severity") == "HIGH"
                        ]
                    ),
                    "medium_severity": len(
                        [
                            r
                            for r in report.get("results", [])
                            if r.get("issue_severity") == "MEDIUM"
                        ]
                    ),
                    "low_severity": len(
                        [
                            r
                            for r in report.get("results", [])
                            if r.get("issue_severity") == "LOW"
                        ]
                    ),
                    "report_file": str(report_file),
                    "details": report,
                }
            return {
                "tool": "bandit",
                "success": False,
                "error": "Report file not generated",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except FileNotFoundError:
            return {
                "tool": "bandit",
                "success": False,
                "error": "bandit not found. Install with: pip install bandit",
            }
        except Exception as e:
            return {"tool": "bandit", "success": False, "error": str(e)}

    def run_safety_scan(self) -> Dict[str, Any]:
        """Run safety scanner for dependency vulnerabilities."""
        print("🛡️  Running safety dependency scan...")

        try:
            # Run safety check with JSON output
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                # No vulnerabilities found
                return {
                    "tool": "safety",
                    "success": True,
                    "vulnerabilities_found": 0,
                    "message": "No known vulnerabilities found in dependencies",
                }
            # Parse JSON output for vulnerabilities
            try:
                vulnerabilities = json.loads(result.stdout)
                return {
                    "tool": "safety",
                    "success": True,
                    "vulnerabilities_found": len(vulnerabilities),
                    "details": vulnerabilities,
                }
            except json.JSONDecodeError:
                return {
                    "tool": "safety",
                    "success": False,
                    "error": "Failed to parse safety output",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

        except FileNotFoundError:
            return {
                "tool": "safety",
                "success": False,
                "error": "safety not found. Install with: pip install safety",
            }
        except Exception as e:
            return {"tool": "safety", "success": False, "error": str(e)}

    def check_secure_coding_patterns(self) -> Dict[str, Any]:
        """Check for secure coding patterns in the codebase."""
        print("📋 Checking secure coding patterns...")

        issues = []
        files_scanned = 0

        # Patterns to check for
        dangerous_patterns = [
            {
                "pattern": r"pickle\.loads?\(",
                "severity": "HIGH",
                "message": "Unsafe pickle usage detected - use secure serialization instead",
                "file_types": [".py"],
            },
            {
                "pattern": r"tarfile\.extractall\(",
                "severity": "HIGH",
                "message": "Unsafe tar extraction - use SecureTarExtractor instead",
                "file_types": [".py"],
            },
            {
                "pattern": r"eval\(",
                "severity": "HIGH",
                "message": "Use of eval() detected - potential code injection risk",
                "file_types": [".py"],
            },
            {
                "pattern": r"exec\(",
                "severity": "HIGH",
                "message": "Use of exec() detected - potential code injection risk",
                "file_types": [".py"],
            },
            {
                "pattern": r"shell=True",
                "severity": "MEDIUM",
                "message": "Use of shell=True in subprocess - potential command injection",
                "file_types": [".py"],
            },
            {
                "pattern": r"password\s*=\s*['\"][^'\"]+['\"]",
                "severity": "HIGH",
                "message": "Hardcoded password detected",
                "file_types": [".py", ".js", ".ts"],
            },
            {
                "pattern": r"SECRET_KEY\s*=\s*['\"][^'\"]+['\"]",
                "severity": "HIGH",
                "message": "Hardcoded secret key detected",
                "file_types": [".py"],
            },
        ]

        import re

        # Scan all source files
        for pattern_info in dangerous_patterns:
            pattern = re.compile(pattern_info["pattern"], re.IGNORECASE)

            for file_ext in pattern_info["file_types"]:
                for file_path in self.src_dir.rglob(f"*{file_ext}"):
                    if file_path.is_file():
                        files_scanned += 1
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()

                            for line_num, line in enumerate(content.splitlines(), 1):
                                if pattern.search(line):
                                    issues.append(
                                        {
                                            "file": str(
                                                file_path.relative_to(self.project_root)
                                            ),
                                            "line": line_num,
                                            "severity": pattern_info["severity"],
                                            "message": pattern_info["message"],
                                            "code": line.strip(),
                                        }
                                    )
                        except (UnicodeDecodeError, PermissionError):
                            # Skip files we can't read
                            continue

        return {
            "tool": "pattern_check",
            "success": True,
            "files_scanned": files_scanned,
            "issues_found": len(issues),
            "high_severity": len([i for i in issues if i["severity"] == "HIGH"]),
            "medium_severity": len([i for i in issues if i["severity"] == "MEDIUM"]),
            "low_severity": len([i for i in issues if i["severity"] == "LOW"]),
            "issues": issues,
        }

    def run_full_scan(self) -> Dict[str, Any]:
        """Run comprehensive security scan."""
        print("🔐 Starting comprehensive security scan...")

        results = {
            "timestamp": os.environ.get("TIMESTAMP", "unknown"),
            "project_root": str(self.project_root),
            "scans": {},
        }

        # Run all scans
        results["scans"]["bandit"] = self.run_bandit_scan()
        results["scans"]["safety"] = self.run_safety_scan()
        results["scans"]["patterns"] = self.check_secure_coding_patterns()

        # Generate summary
        total_issues = 0
        total_high = 0
        total_medium = 0
        total_low = 0

        for scan_name, scan_result in results["scans"].items():
            if scan_result.get("success"):
                total_issues += scan_result.get("issues_found", 0) + scan_result.get(
                    "vulnerabilities_found", 0
                )
                total_high += scan_result.get("high_severity", 0)
                total_medium += scan_result.get("medium_severity", 0)
                total_low += scan_result.get("low_severity", 0)

        results["summary"] = {
            "total_issues": total_issues,
            "high_severity": total_high,
            "medium_severity": total_medium,
            "low_severity": total_low,
            "security_score": max(
                0, 100 - (total_high * 20) - (total_medium * 5) - (total_low * 1)
            ),
        }

        return results

    def generate_report(
        self, results: Dict[str, Any], output_file: Path = None
    ) -> None:
        """Generate a formatted security report."""
        if output_file is None:
            output_file = self.project_root / "security-report.json"

        # Save detailed JSON report
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        # Print summary to console
        print("\n" + "=" * 60)
        print("🔐 SECURITY SCAN SUMMARY")
        print("=" * 60)

        summary = results.get("summary", {})
        print(f"Total Issues Found: {summary.get('total_issues', 0)}")
        print(f"  🔴 High Severity: {summary.get('high_severity', 0)}")
        print(f"  🟡 Medium Severity: {summary.get('medium_severity', 0)}")
        print(f"  🟢 Low Severity: {summary.get('low_severity', 0)}")
        print(f"Security Score: {summary.get('security_score', 0)}/100")

        # Print scan details
        for scan_name, scan_result in results.get("scans", {}).items():
            print(f"\n📊 {scan_name.upper()} SCAN:")
            if scan_result.get("success"):
                if scan_name == "patterns":
                    print(f"  Files Scanned: {scan_result.get('files_scanned', 0)}")
                    print(f"  Issues Found: {scan_result.get('issues_found', 0)}")
                elif scan_name == "safety":
                    print(
                        f"  Vulnerabilities: {scan_result.get('vulnerabilities_found', 0)}"
                    )
                elif scan_name == "bandit":
                    print(f"  Issues Found: {scan_result.get('issues_found', 0)}")
                    if scan_result.get("report_file"):
                        print(f"  Report: {scan_result['report_file']}")
            else:
                print(f"  ❌ Failed: {scan_result.get('error', 'Unknown error')}")

        print(f"\n📄 Detailed report saved to: {output_file}")

        # Exit with appropriate code
        if summary.get("high_severity", 0) > 0:
            print("\n❌ SCAN FAILED: High severity issues found!")
            return False
        if summary.get("total_issues", 0) > 0:
            print("\n⚠️  SCAN WARNING: Security issues found")
            return True
        print("\n✅ SCAN PASSED: No security issues found")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Security scanner for sandbox-core")
    parser.add_argument(
        "--project-root",
        "-p",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--output", "-o", type=Path, help="Output file for detailed report"
    )
    parser.add_argument(
        "--fail-on-medium", action="store_true", help="Fail on medium severity issues"
    )

    args = parser.parse_args()

    # Ensure we're in the right directory
    project_root = args.project_root.resolve()
    if not (project_root / "src").exists():
        print(f"❌ No 'src' directory found in {project_root}")
        print("Make sure you're running from the sandbox-core directory")
        sys.exit(1)

    # Run security scan
    scanner = SecurityScanner(project_root)
    results = scanner.run_full_scan()
    success = scanner.generate_report(results, args.output)

    # Exit with appropriate code
    summary = results.get("summary", {})
    if summary.get("high_severity", 0) > 0:
        sys.exit(1)  # Fail on high severity
    elif args.fail_on_medium and summary.get("medium_severity", 0) > 0:
        sys.exit(1)  # Fail on medium if requested
    elif not success:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
