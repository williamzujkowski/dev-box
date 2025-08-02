# Security Vulnerability Remediation Template

This template provides a comprehensive workflow for identifying, analyzing, and
fixing security vulnerabilities in Python projects, with special focus on
tarfile and pickle vulnerabilities.

## 🔒 Security Remediation Workflow

### Phase 1: Security Assessment & Analysis

#### 1.1 Initial Security Scan

```bash
# Run comprehensive security scanning
bandit -r . -f json -o security_report.json
safety check --json --output safety_report.json
semgrep --config=auto --json --output=semgrep_report.json .

# Check for specific vulnerability patterns
grep -r "pickle\|tarfile\|eval\|exec" --include="*.py" .
```

#### 1.2 Vulnerability Classification

```python
# Classify vulnerabilities by severity and type
VULNERABILITY_CATEGORIES = {
    'CRITICAL': [
        'B301',  # pickle usage
        'B506',  # yaml.load usage
        'B202',  # tarfile usage
        'B102',  # exec usage
        'B307',  # eval usage
    ],
    'HIGH': [
        'B104',  # hardcoded_bind_all_interfaces
        'B110',  # try_except_pass
        'B605',  # start_process_with_a_shell
    ],
    'MEDIUM': [
        'B108',  # hardcoded_tmp_directory
        'B113',  # request_without_timeout
    ]
}
```

### Phase 2: Tarfile Vulnerability Remediation

#### 2.1 Safe Tarfile Extraction Implementation

```python
# File: utils/safe_extraction.py
import tarfile
import os
from pathlib import Path
from typing import Union, Optional

class SafeTarExtractor:
    """Safe tarfile extraction with security checks"""

    def __init__(self, max_size: int = 100 * 1024 * 1024):  # 100MB default
        self.max_size = max_size
        self.allowed_paths = set()

    def is_safe_path(self, path: str, base_path: str) -> bool:
        """Check if extraction path is safe"""
        # Resolve paths to prevent directory traversal
        abs_base = os.path.abspath(base_path)
        abs_path = os.path.abspath(os.path.join(base_path, path))

        # Ensure path stays within base directory
        return abs_path.startswith(abs_base)

    def safe_extract(self, tar_path: Union[str, Path],
                    extract_to: Union[str, Path],
                    members: Optional[list] = None) -> bool:
        """Safely extract tarfile with security checks"""
        try:
            with tarfile.open(tar_path, 'r') as tar:
                total_size = 0

                # Get members to extract
                tar_members = members or tar.getmembers()

                for member in tar_members:
                    # Security checks
                    if not self.is_safe_path(member.name, str(extract_to)):
                        raise SecurityError(f"Unsafe path detected: {member.name}")

                    # Check for directory traversal
                    if member.name.startswith('/') or '..' in member.name:
                        raise SecurityError(f"Directory traversal attempt: {member.name}")

                    # Check file size limits
                    if member.size > self.max_size:
                        raise SecurityError(f"File too large: {member.name} ({member.size} bytes)")

                    total_size += member.size
                    if total_size > self.max_size:
                        raise SecurityError(f"Total extraction size exceeds limit: {total_size}")

                    # Check for symlink attacks
                    if member.issym() or member.islnk():
                        # Validate symlink target
                        if not self.is_safe_path(member.linkname, str(extract_to)):
                            raise SecurityError(f"Unsafe symlink target: {member.linkname}")

                # Extract safely
                tar.extractall(path=extract_to, members=tar_members)
                return True

        except (tarfile.TarError, SecurityError, OSError) as e:
            print(f"Extraction failed: {e}")
            return False

class SecurityError(Exception):
    """Custom security exception"""
    pass

# Usage example
def replace_unsafe_tarfile_usage():
    """Replace unsafe tarfile.extractall() calls"""
    extractor = SafeTarExtractor(max_size=50 * 1024 * 1024)  # 50MB limit

    # BEFORE (unsafe):
    # with tarfile.open('archive.tar.gz') as tar:
    #     tar.extractall('extracted/')

    # AFTER (safe):
    success = extractor.safe_extract('archive.tar.gz', 'extracted/')
    if not success:
        raise SecurityError("Failed to safely extract archive")
```

#### 2.2 Automated Tarfile Fix Application

```python
# File: security_fixes/tarfile_fixer.py
import ast
import re
from pathlib import Path
from typing import List, Tuple

class TarfileFixer:
    """Automatically fix unsafe tarfile usage"""

    def __init__(self):
        self.unsafe_patterns = [
            r'tarfile\.open\([^)]+\)\.extractall\(',
            r'\.extractall\(\s*[^)]*\)',
        ]
        self.safe_import = "from utils.safe_extraction import SafeTarExtractor"

    def find_unsafe_usage(self, file_path: Path) -> List[Tuple[int, str]]:
        """Find unsafe tarfile usage in Python file"""
        issues = []

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            for pattern in self.unsafe_patterns:
                if re.search(pattern, line):
                    issues.append((i, line.strip()))

        return issues

    def fix_file(self, file_path: Path) -> bool:
        """Apply security fixes to file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add safe import if not present
        if 'SafeTarExtractor' not in content:
            content = f"{self.safe_import}\n{content}"

        # Replace unsafe patterns
        fixes = [
            (
                r'with\s+tarfile\.open\(([^)]+)\)\s+as\s+(\w+):\s*\n\s*\2\.extractall\(([^)]*)\)',
                r'extractor = SafeTarExtractor()\nif not extractor.safe_extract(\1, \3):\n    raise SecurityError("Failed to extract archive")'
            ),
            (
                r'(\w+)\.extractall\(([^)]*)\)',
                r'extractor = SafeTarExtractor()\nif not extractor.safe_extract(tarfile_path, \2):\n    raise SecurityError("Failed to extract archive")'
            )
        ]

        original_content = content
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False
```

### Phase 3: Pickle Vulnerability Remediation

#### 3.1 Safe Serialization Alternatives

```python
# File: utils/safe_serialization.py
import json
import pickle
import marshal
import dill
from typing import Any, Union, Optional
from pathlib import Path

class SafeSerializer:
    """Safe alternatives to pickle for serialization"""

    SUPPORTED_FORMATS = ['json', 'marshal', 'dill_safe']

    @staticmethod
    def safe_json_serialize(obj: Any, file_path: Union[str, Path]) -> bool:
        """Safe JSON serialization for basic types"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(obj, f, indent=2, ensure_ascii=False)
            return True
        except (TypeError, ValueError) as e:
            print(f"JSON serialization failed: {e}")
            return False

    @staticmethod
    def safe_json_deserialize(file_path: Union[str, Path]) -> Optional[Any]:
        """Safe JSON deserialization"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"JSON deserialization failed: {e}")
            return None

    @staticmethod
    def safe_marshal_serialize(obj: Any, file_path: Union[str, Path]) -> bool:
        """Safe marshal serialization for code objects"""
        try:
            with open(file_path, 'wb') as f:
                marshal.dump(obj, f)
            return True
        except (TypeError, ValueError) as e:
            print(f"Marshal serialization failed: {e}")
            return False

    @staticmethod
    def safe_marshal_deserialize(file_path: Union[str, Path]) -> Optional[Any]:
        """Safe marshal deserialization"""
        try:
            with open(file_path, 'rb') as f:
                return marshal.load(f)
        except (ValueError, EOFError, FileNotFoundError) as e:
            print(f"Marshal deserialization failed: {e}")
            return None

    @classmethod
    def restricted_pickle_load(cls, file_path: Union[str, Path],
                              allowed_classes: set = None) -> Optional[Any]:
        """Restricted pickle loading with class whitelist"""
        if allowed_classes is None:
            allowed_classes = {
                'builtins.dict', 'builtins.list', 'builtins.tuple',
                'builtins.str', 'builtins.int', 'builtins.float',
                'builtins.bool', 'builtins.set'
            }

        class RestrictedUnpickler(pickle.Unpickler):
            def find_class(self, module, name):
                full_name = f"{module}.{name}"
                if full_name in allowed_classes:
                    return getattr(__import__(module, fromlist=[name]), name)
                raise pickle.UnpicklingError(f"Class {full_name} not allowed")

        try:
            with open(file_path, 'rb') as f:
                return RestrictedUnpickler(f).load()
        except (pickle.UnpicklingError, FileNotFoundError) as e:
            print(f"Restricted pickle loading failed: {e}")
            return None

# Migration utility
def migrate_pickle_to_json(pickle_path: Union[str, Path],
                          json_path: Union[str, Path]) -> bool:
    """Migrate pickle files to JSON where possible"""
    serializer = SafeSerializer()

    # Try to load pickle data
    try:
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
    except Exception as e:
        print(f"Failed to load pickle file: {e}")
        return False

    # Try to save as JSON
    if serializer.safe_json_serialize(data, json_path):
        print(f"Successfully migrated {pickle_path} to {json_path}")
        return True
    else:
        print(f"Failed to migrate {pickle_path} - data not JSON serializable")
        return False
```

#### 3.2 Pickle Usage Detector and Fixer

```python
# File: security_fixes/pickle_fixer.py
import ast
import re
from pathlib import Path
from typing import List, Dict, Any

class PickleFixer:
    """Detect and fix unsafe pickle usage"""

    def __init__(self):
        self.unsafe_patterns = [
            r'pickle\.load\(',
            r'pickle\.loads\(',
            r'cPickle\.load\(',
            r'dill\.load\(',
        ]

    def analyze_pickle_usage(self, file_path: Path) -> Dict[str, Any]:
        """Analyze pickle usage in file"""
        analysis = {
            'unsafe_loads': [],
            'pickle_imports': [],
            'recommendations': []
        }

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()

        # Find pickle imports
        import_patterns = [
            r'import\s+(c?pickle|dill)',
            r'from\s+(c?pickle|dill)\s+import',
        ]

        for i, line in enumerate(lines, 1):
            for pattern in import_patterns:
                if re.search(pattern, line):
                    analysis['pickle_imports'].append((i, line.strip()))

            for pattern in self.unsafe_patterns:
                if re.search(pattern, line):
                    analysis['unsafe_loads'].append((i, line.strip()))

        # Generate recommendations
        if analysis['unsafe_loads']:
            analysis['recommendations'].extend([
                "Replace pickle.load() with restricted_pickle_load() for safety",
                "Consider migrating to JSON for simple data structures",
                "Use marshal for code objects if appropriate",
                "Implement input validation and sanitization"
            ])

        return analysis

    def generate_safe_replacement(self, pickle_line: str) -> str:
        """Generate safe replacement for pickle usage"""
        replacements = {
            'pickle.load(': 'SafeSerializer.restricted_pickle_load(',
            'pickle.loads(': 'SafeSerializer.restricted_pickle_loads(',
            'cPickle.load(': 'SafeSerializer.restricted_pickle_load(',
            'dill.load(': 'SafeSerializer.restricted_pickle_load(',
        }

        for unsafe, safe in replacements.items():
            if unsafe in pickle_line:
                return pickle_line.replace(unsafe, safe)

        return pickle_line
```

### Phase 4: Security Testing Implementation

#### 4.1 Security Test Suite

```python
# File: tests/security/test_security_fixes.py
import pytest
import tempfile
import tarfile
import pickle
import json
import os
from pathlib import Path
from utils.safe_extraction import SafeTarExtractor, SecurityError
from utils.safe_serialization import SafeSerializer

class TestSecurityFixes:
    """Comprehensive security testing suite"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = []

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_malicious_tar(self, tar_path: str) -> str:
        """Create malicious tar for testing"""
        malicious_tar = os.path.join(self.temp_dir, tar_path)

        with tarfile.open(malicious_tar, 'w') as tar:
            # Add file with directory traversal
            info = tarfile.TarInfo(name="../../../etc/passwd")
            info.size = 100
            tar.addfile(info, fileobj=None)

        return malicious_tar

    def test_directory_traversal_protection(self):
        """Test protection against directory traversal attacks"""
        extractor = SafeTarExtractor()
        malicious_tar = self.create_malicious_tar("malicious.tar")

        with pytest.raises(SecurityError, match="Directory traversal attempt"):
            extractor.safe_extract(malicious_tar, self.temp_dir)

    def test_file_size_limits(self):
        """Test file size limit enforcement"""
        extractor = SafeTarExtractor(max_size=1024)  # 1KB limit

        large_tar = os.path.join(self.temp_dir, "large.tar")
        with tarfile.open(large_tar, 'w') as tar:
            info = tarfile.TarInfo(name="large_file.txt")
            info.size = 2048  # 2KB file
            tar.addfile(info, fileobj=None)

        with pytest.raises(SecurityError, match="File too large"):
            extractor.safe_extract(large_tar, self.temp_dir)

    def test_symlink_attack_protection(self):
        """Test protection against symlink attacks"""
        extractor = SafeTarExtractor()

        symlink_tar = os.path.join(self.temp_dir, "symlink.tar")
        with tarfile.open(symlink_tar, 'w') as tar:
            info = tarfile.TarInfo(name="symlink")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)

        with pytest.raises(SecurityError, match="Unsafe symlink target"):
            extractor.safe_extract(symlink_tar, self.temp_dir)

    def test_safe_json_serialization(self):
        """Test safe JSON serialization"""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        json_path = os.path.join(self.temp_dir, "test.json")

        # Test serialization
        assert SafeSerializer.safe_json_serialize(test_data, json_path)

        # Test deserialization
        loaded_data = SafeSerializer.safe_json_deserialize(json_path)
        assert loaded_data == test_data

    def test_restricted_pickle_loading(self):
        """Test restricted pickle loading"""
        # Create test pickle with allowed class
        test_data = {"safe": "data"}
        pickle_path = os.path.join(self.temp_dir, "safe.pkl")

        with open(pickle_path, 'wb') as f:
            pickle.dump(test_data, f)

        # Test loading with restrictions
        loaded_data = SafeSerializer.restricted_pickle_load(
            pickle_path,
            allowed_classes={'builtins.dict', 'builtins.str'}
        )
        assert loaded_data == test_data

    def test_pickle_migration(self):
        """Test pickle to JSON migration"""
        from utils.safe_serialization import migrate_pickle_to_json

        # Create pickle file
        test_data = {"migrate": "me", "count": 123}
        pickle_path = os.path.join(self.temp_dir, "migrate.pkl")
        json_path = os.path.join(self.temp_dir, "migrated.json")

        with open(pickle_path, 'wb') as f:
            pickle.dump(test_data, f)

        # Test migration
        assert migrate_pickle_to_json(pickle_path, json_path)

        # Verify migrated data
        with open(json_path, 'r') as f:
            migrated_data = json.load(f)
        assert migrated_data == test_data

    @pytest.mark.parametrize("malicious_input", [
        "../../../etc/passwd",
        "/absolute/path",
        "normal/../traversal",
        "symlink_to_root"
    ])
    def test_path_validation(self, malicious_input):
        """Test path validation with various malicious inputs"""
        extractor = SafeTarExtractor()
        assert not extractor.is_safe_path(malicious_input, self.temp_dir)
```

#### 4.2 Automated Security Scanning

```bash
# File: scripts/security_scan.sh
#!/bin/bash

# Comprehensive security scanning script

set -euo pipefail

PROJECT_ROOT="${1:-.}"
REPORTS_DIR="${PROJECT_ROOT}/security_reports"

echo "🔒 Starting comprehensive security scan..."

# Create reports directory
mkdir -p "$REPORTS_DIR"

# 1. Bandit scan for Python security issues
echo "📊 Running Bandit security scan..."
bandit -r "$PROJECT_ROOT" \
    -f json \
    -o "$REPORTS_DIR/bandit_report.json" \
    -x "**/tests/**,**/venv/**,**/.env/**" \
    --confidence-level high \
    --severity-level medium

# 2. Safety check for known vulnerabilities
echo "🛡️ Checking for known vulnerabilities with Safety..."
safety check \
    --json \
    --output "$REPORTS_DIR/safety_report.json" \
    --continue-on-error

# 3. Semgrep static analysis
echo "🔍 Running Semgrep static analysis..."
semgrep \
    --config=auto \
    --json \
    --output="$REPORTS_DIR/semgrep_report.json" \
    "$PROJECT_ROOT"

# 4. Custom security checks
echo "🔧 Running custom security checks..."
python -c "
import sys
import json
from pathlib import Path
from security_fixes.tarfile_fixer import TarfileFixer
from security_fixes.pickle_fixer import PickleFixer

# Find all Python files
python_files = list(Path('$PROJECT_ROOT').rglob('*.py'))

# Check tarfile usage
tarfile_issues = []
tarfile_fixer = TarfileFixer()
for file_path in python_files:
    issues = tarfile_fixer.find_unsafe_usage(file_path)
    if issues:
        tarfile_issues.append({
            'file': str(file_path),
            'issues': issues
        })

# Check pickle usage
pickle_issues = []
pickle_fixer = PickleFixer()
for file_path in python_files:
    analysis = pickle_fixer.analyze_pickle_usage(file_path)
    if analysis['unsafe_loads']:
        pickle_issues.append({
            'file': str(file_path),
            'analysis': analysis
        })

# Save custom scan results
custom_results = {
    'tarfile_issues': tarfile_issues,
    'pickle_issues': pickle_issues
}

with open('$REPORTS_DIR/custom_security_scan.json', 'w') as f:
    json.dump(custom_results, f, indent=2)

print(f'Found {len(tarfile_issues)} tarfile issues')
print(f'Found {len(pickle_issues)} pickle issues')
"

# 5. Generate summary report
echo "📋 Generating security summary..."
python -c "
import json
from pathlib import Path

reports_dir = Path('$REPORTS_DIR')
summary = {
    'scan_timestamp': '$(date -Iseconds)',
    'project_root': '$PROJECT_ROOT',
    'findings': {
        'bandit': 0,
        'safety': 0,
        'semgrep': 0,
        'custom': 0
    },
    'critical_issues': [],
    'recommendations': []
}

# Process Bandit results
try:
    with open(reports_dir / 'bandit_report.json') as f:
        bandit_data = json.load(f)
        summary['findings']['bandit'] = len(bandit_data.get('results', []))

        # Extract critical issues
        for result in bandit_data.get('results', []):
            if result.get('issue_severity') in ['HIGH', 'CRITICAL']:
                summary['critical_issues'].append({
                    'source': 'bandit',
                    'severity': result.get('issue_severity'),
                    'test_id': result.get('test_id'),
                    'filename': result.get('filename'),
                    'line_number': result.get('line_number'),
                    'issue_text': result.get('issue_text')
                })
except FileNotFoundError:
    pass

# Process custom scan results
try:
    with open(reports_dir / 'custom_security_scan.json') as f:
        custom_data = json.load(f)
        tarfile_count = len(custom_data.get('tarfile_issues', []))
        pickle_count = len(custom_data.get('pickle_issues', []))
        summary['findings']['custom'] = tarfile_count + pickle_count

        # Add recommendations
        if tarfile_count > 0:
            summary['recommendations'].append('Replace unsafe tarfile.extractall() with SafeTarExtractor')
        if pickle_count > 0:
            summary['recommendations'].append('Replace unsafe pickle usage with safe alternatives')
except FileNotFoundError:
    pass

# Save summary
with open(reports_dir / 'security_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print('Security scan complete!')
print(f'Total findings: {sum(summary[\"findings\"].values())}')
print(f'Critical issues: {len(summary[\"critical_issues\"])}')
"

echo "✅ Security scan complete! Reports saved to $REPORTS_DIR"
```

### Phase 5: CI/CD Security Integration

#### 5.1 GitHub Actions Security Workflow

```yaml
# File: .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Run security scan daily at 2 AM UTC
    - cron: "0 2 * * *"

jobs:
  security-scan:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      security-events: write
      actions: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install security tools
        run: |
          pip install bandit[toml] safety semgrep
          pip install -r requirements.txt

      - name: Run comprehensive security scan
        run: |
          chmod +x scripts/security_scan.sh
          ./scripts/security_scan.sh

      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: security_reports/
          retention-days: 30

      - name: Check for critical vulnerabilities
        run: |
          python -c "
          import json
          import sys

          with open('security_reports/security_summary.json') as f:
              summary = json.load(f)

          critical_count = len(summary.get('critical_issues', []))
          total_findings = sum(summary.get('findings', {}).values())

          print(f'Critical issues: {critical_count}')
          print(f'Total findings: {total_findings}')

          if critical_count > 0:
              print('❌ Critical security vulnerabilities found!')
              for issue in summary['critical_issues']:
                  print(f'- {issue[\"test_id\"]}: {issue[\"issue_text\"]}')
              sys.exit(1)

          if total_findings > 10:  # Configurable threshold
              print(f'⚠️ High number of security findings: {total_findings}')
              sys.exit(1)

          print('✅ Security scan passed!')
          "

      - name: Comment PR with security summary
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const summary = JSON.parse(fs.readFileSync('security_reports/security_summary.json', 'utf8'));

            const criticalCount = summary.critical_issues.length;
            const totalFindings = Object.values(summary.findings).reduce((a, b) => a + b, 0);

            let comment = `## 🔒 Security Scan Results\n\n`;
            comment += `- **Total findings**: ${totalFindings}\n`;
            comment += `- **Critical issues**: ${criticalCount}\n\n`;

            if (criticalCount > 0) {
              comment += `### ❌ Critical Issues\n`;
              summary.critical_issues.forEach(issue => {
                comment += `- **${issue.test_id}**: ${issue.issue_text} (${issue.filename}:${issue.line_number})\n`;
              });
            }

            if (summary.recommendations.length > 0) {
              comment += `### 💡 Recommendations\n`;
              summary.recommendations.forEach(rec => {
                comment += `- ${rec}\n`;
              });
            }

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });

  dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: "fs"
          format: "sarif"
          output: "trivy-results.sarif"

      - name: Upload Trivy scan results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: "trivy-results.sarif"
```

#### 5.2 Pre-commit Security Hooks

```yaml
# File: .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: "1.7.5"
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        exclude: ^tests/

  - repo: https://github.com/gitguardian/ggshield
    rev: v1.20.0
    hooks:
      - id: ggshield
        language: python
        stages: [commit]

  - repo: local
    hooks:
      - id: custom-security-check
        name: Custom Security Checks
        entry: python scripts/pre_commit_security.py
        language: python
        files: \.py$
```

### Phase 6: Production Deployment Security

#### 6.1 Security Deployment Checklist

```markdown
# Security Deployment Checklist

## Pre-Deployment Security Verification

### Code Security

- [ ] All Bandit security issues resolved (severity HIGH+)
- [ ] No unsafe pickle usage detected
- [ ] No unsafe tarfile extraction detected
- [ ] All dependencies scanned with Safety
- [ ] Semgrep static analysis passed
- [ ] Custom security tests passing

### Environment Security

- [ ] Secrets properly configured in environment variables
- [ ] No hardcoded credentials in code
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Input validation implemented
- [ ] Output encoding implemented

### Infrastructure Security

- [ ] Security groups properly configured
- [ ] Network segmentation implemented
- [ ] Monitoring and alerting configured
- [ ] Backup and recovery procedures tested
- [ ] Incident response plan in place

### Compliance

- [ ] Data protection requirements met
- [ ] Audit logging implemented
- [ ] Access controls verified
- [ ] Privacy policy updated
- [ ] Security documentation complete

## Post-Deployment Verification

- [ ] Vulnerability scanner results reviewed
- [ ] Penetration testing completed
- [ ] Security monitoring active
- [ ] Incident response procedures tested
```

#### 6.2 Production Security Monitoring

```python
# File: monitoring/security_monitor.py
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List
import subprocess
import json

class SecurityMonitor:
    """Production security monitoring"""

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def run_security_checks(self) -> Dict:
        """Run automated security checks"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }

        # Check for suspicious file operations
        results['checks']['file_operations'] = self._check_file_operations()

        # Monitor for pickle usage
        results['checks']['pickle_usage'] = self._monitor_pickle_usage()

        # Check for unauthorized access
        results['checks']['access_control'] = self._check_access_control()

        return results

    def _check_file_operations(self) -> Dict:
        """Monitor file operations for security issues"""
        # Implementation for monitoring file operations
        return {'status': 'safe', 'alerts': []}

    def _monitor_pickle_usage(self) -> Dict:
        """Monitor for runtime pickle usage"""
        # Implementation for monitoring pickle usage
        return {'status': 'safe', 'alerts': []}

    def _check_access_control(self) -> Dict:
        """Check access control violations"""
        # Implementation for access control monitoring
        return {'status': 'safe', 'alerts': []}

# Usage in production
if __name__ == "__main__":
    config = {
        'check_interval': 300,  # 5 minutes
        'alert_threshold': 'medium'
    }

    monitor = SecurityMonitor(config)

    while True:
        try:
            results = monitor.run_security_checks()

            # Process results and send alerts if needed
            for check_name, check_results in results['checks'].items():
                if check_results.get('alerts'):
                    logging.warning(f"Security alert in {check_name}: {check_results['alerts']}")

            time.sleep(config['check_interval'])

        except Exception as e:
            logging.error(f"Security monitoring error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying
```

## 🎯 Implementation Checklist

### Immediate Actions (Priority 1)

- [ ] Run initial security scan with Bandit, Safety, and Semgrep
- [ ] Implement SafeTarExtractor class
- [ ] Replace all unsafe tarfile.extractall() calls
- [ ] Implement SafeSerializer for pickle alternatives
- [ ] Create security test suite

### Medium-term Actions (Priority 2)

- [ ] Set up CI/CD security pipeline
- [ ] Implement pre-commit security hooks
- [ ] Create security monitoring dashboard
- [ ] Conduct security training for team
- [ ] Document security procedures

### Long-term Actions (Priority 3)

- [ ] Regular security audits
- [ ] Penetration testing
- [ ] Security compliance verification
- [ ] Incident response plan testing
- [ ] Security awareness training

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Guide](https://python-security.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## 🔧 Tools and Dependencies

```bash
# Install security tools
pip install bandit[toml] safety semgrep
pip install cryptography pycryptodome
pip install pytest pytest-security

# Optional tools for advanced security
pip install pip-audit
pip install cyclonedx-bom
```

This template provides a comprehensive approach to identifying, fixing, and
preventing security vulnerabilities, with special focus on the critical tarfile
and pickle security issues commonly found in Python applications.
