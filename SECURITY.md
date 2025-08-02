# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities to our security team:
- Email: security@dev-box-project.org
- Response time: 48 hours
- Update frequency: Weekly

## Security Fixes Implemented

### CVE-2025-4517: Tarfile Path Traversal
- **Status**: Fixed
- **Description**: Unsafe `tarfile.extractall()` usage
- **Solution**: Safe extraction wrapper in `src/safe_extract.py`
- **Impact**: Prevents arbitrary file overwrites

### CWE-502: Pickle Deserialization
- **Status**: Mitigated
- **Description**: Unsafe pickle deserialization
- **Solution**: Secure JSON serializer in `src/secure_serialization.py`
- **Impact**: Prevents remote code execution

## Security Tools Integration

### Automated Scanning
- **Bandit**: Python security linting
- **Safety**: Dependency vulnerability scanning
- **flake8-security**: Additional security checks

### CI/CD Security Gates
- High-severity findings block deployment
- Dependency vulnerability scanning
- Regular security audits

## Secure Development Practices

### File Extraction
```python
# ❌ UNSAFE
import tarfile
with tarfile.open('file.tar') as tar:
    tar.extractall('/path')  # Vulnerable to path traversal

# ✅ SAFE
from src.safe_extract import safe_extractall
safe_extractall('file.tar', '/path')
```

### Data Serialization
```python
# ❌ UNSAFE
import pickle
obj = pickle.loads(data)  # Vulnerable to RCE

# ✅ SAFE
from src.secure_serialization import safe_loads
obj = safe_loads(data, secret_key)
```

### Environment Variables
- Use environment variables for secrets
- Never commit sensitive data
- Implement proper secret rotation

## Security Checklist

- [ ] All file extractions use safe wrapper
- [ ] No pickle deserialization of untrusted data
- [ ] Secrets stored in environment variables
- [ ] Dependencies regularly updated
- [ ] Security scans pass in CI
- [ ] Code review includes security considerations

## Security Updates

Stay informed about security updates:
- Watch this repository for security advisories
- Subscribe to security notifications
- Regular dependency updates
- Follow security best practices

For questions about security practices, contact the development team.
