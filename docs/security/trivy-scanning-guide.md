# Trivy Vulnerability Scanning Guide

## Overview

This document describes the comprehensive Trivy vulnerability scanning implementation for the dev-box project. The enhanced scanning configuration provides multi-layered security analysis with detailed reporting and CI/CD integration.

## Enhanced Features

### 🔍 Matrix Scanning Strategy

The enhanced workflow implements a matrix-based scanning approach that tests multiple artifact types in parallel:

1. **Filesystem Scanning** - Complete repository vulnerability analysis
2. **SBOM Generation** - Software Bill of Materials in SPDX format
3. **Python Dependencies** - Scan `sandbox-core` Python packages
4. **Node.js Dependencies** - Scan npm packages in `package.json`
5. **Docker Image Scanning** - Scan base images (Ubuntu 24.04)

### 🛡️ Security Configuration

#### Severity Levels
- **CRITICAL & HIGH**: Fail CI/CD pipeline (exit-code: 1)
- **MEDIUM**: Report but don't fail (for awareness)
- **LOW & UNKNOWN**: Included in SBOM but not in main scans

#### Exclusions Strategy
The scanning configuration excludes development-specific files that commonly generate false positives:

**Test & Documentation Files:**
- `**/tests/**`, `**/test/**`, `**/*_test.*`
- `**/docs/**`, `**/*.md`, `**/*.rst`, `**/*.txt`

**Build Artifacts:**
- `**/node_modules/**`, `**/build/**`, `**/dist/**`
- `**/__pycache__/**`, `**/*.pyc`

**Development Environment:**
- `**/.vscode/**`, `**/.idea/**`
- `**/venv/**`, `**/.venv/**`
- `**/Vagrantfile*`, `**/.vagrant/**`

**Known Safe Files:**
- `**/sandbox-core/requirements-security.txt` (security tools themselves)

### 📊 Reporting Features

#### GitHub Security Integration
- **SARIF Upload**: Results automatically appear in GitHub Security tab
- **Categorized Results**: Each scan type has its own category
- **Historical Tracking**: Security trends over time

#### Human-Readable Reports
- **Step Summaries**: Real-time results in GitHub Actions summary
- **PR Comments**: Detailed security reports added to pull requests
- **Vulnerability Counts**: Clear severity breakdowns
- **Component Analysis**: SBOM component counting

#### Artifacts & Retention
- **30-day retention**: All scan results stored as GitHub artifacts
- **Multiple formats**: SARIF, JSON, table, SPDX-JSON
- **Comprehensive reports**: Combined security analysis documents

## Workflow Configuration

### Matrix Job Configuration

```yaml
strategy:
  fail-fast: false
  matrix:
    scan-type:
      - name: "filesystem"
        type: "fs"
        target: "."
        format: "sarif"
        severity: "CRITICAL,HIGH,MEDIUM"
        exit-code: "1"
      # ... additional scan types
```

### Comprehensive Scan Job

The second job performs an in-depth analysis with:
- **JSON output** for detailed parsing
- **Critical/High focus** with pipeline failure
- **Comprehensive exclusions** tailored to dev-box
- **Advanced reporting** with vulnerability details

## Usage Instructions

### Local Testing

Before deploying changes, test the scanning configuration locally:

```bash
# Run the comprehensive test suite
./scripts/test-trivy-scanning.sh

# Manual Trivy tests
trivy fs --severity HIGH,CRITICAL .
trivy fs --format spdx-json --output sbom.json .
```

### CI/CD Integration

The workflow automatically runs on:
- **Push to main** - Full security validation
- **Pull requests** - Security impact assessment  
- **Weekly schedule** - Routine security monitoring (Tuesdays 4 AM UTC)

### Interpreting Results

#### Exit Codes
- **0**: No HIGH/CRITICAL vulnerabilities found
- **1**: HIGH/CRITICAL vulnerabilities detected (CI fails)

#### Security Tab Results
1. Navigate to repository **Security** tab
2. Select **Code scanning alerts**
3. Filter by tool: **Trivy**
4. Review categorized results by scan type

#### PR Comments
Pull requests automatically receive detailed security reports including:
- Vulnerability summary table
- Top critical/high findings
- Scan configuration details
- Recommendations for remediation

## Maintenance

### Adding Exclusions

To exclude additional false positives:

1. **Edit workflow file**: `.github/workflows/artifact-scan.yml`
2. **Update ignore patterns**: Add to `.trivyignore` creation steps
3. **Test locally**: Run `./scripts/test-trivy-scanning.sh`
4. **Document rationale**: Add comments explaining exclusions

### Updating Scan Targets

To modify scanning scope:

1. **Matrix configuration**: Update `matrix.scan-type` targets
2. **Skip directories**: Modify `skip-dirs` parameters
3. **Severity filters**: Adjust severity levels per scan type
4. **Exit codes**: Configure failure conditions

### Security Tool Updates

Regular maintenance tasks:
- **Trivy version**: Update `aquasecurity/trivy-action` version
- **Database updates**: Trivy automatically updates vulnerability database
- **False positive review**: Quarterly review of exclusions
- **New scan types**: Evaluate additional Trivy scan capabilities

## Troubleshooting

### Common Issues

#### "No vulnerabilities found" 
- Check if exclusions are too broad
- Verify target paths exist
- Review severity filters

#### "Scan timeout"
- Increase timeout values in workflow
- Check for large dependency trees
- Consider excluding large directories

#### "SARIF upload failed"
- Verify GitHub token permissions
- Check SARIF file format validity
- Ensure security-events write permission

### Debug Techniques

1. **Enable debug output**: Add `ACTIONS_STEP_DEBUG: true` to workflow
2. **Local reproduction**: Use test script with verbose flags
3. **Artifact inspection**: Download scan artifacts for detailed analysis
4. **Matrix job isolation**: Disable specific scan types to isolate issues

## Security Best Practices

### Regular Reviews
- **Weekly**: Monitor security tab alerts
- **Monthly**: Review and triage findings
- **Quarterly**: Update exclusions and configurations
- **Annually**: Comprehensive security audit

### Response Procedures
1. **Critical vulnerabilities**: Immediate patching required
2. **High vulnerabilities**: Patch within 7 days
3. **Medium vulnerabilities**: Patch within 30 days
4. **False positives**: Document and exclude appropriately

### Development Integration
- **Pre-commit hooks**: Consider local Trivy scanning
- **IDE integration**: Security linting during development
- **Dependency updates**: Regular automated updates
- **Security training**: Keep team informed on vulnerability management

## Related Documentation

- [GitHub Security Features](https://docs.github.com/en/code-security)
- [Trivy Official Documentation](https://aquasecurity.github.io/trivy/)
- [SARIF Format Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [SPDX SBOM Standard](https://spdx.dev/)

---

*This configuration implements defense-in-depth security scanning appropriate for development environments while minimizing false positive noise that could reduce developer productivity.*