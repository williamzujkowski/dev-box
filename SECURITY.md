# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it privately:

### How to Report

1. **Email**: Send details to security@dev-box.dev (if available) or create a private security advisory
2. **GitHub Security Advisory**: Use GitHub's [private vulnerability reporting](https://github.com/williamzujkowski/dev-box/security/advisories/new)
3. **Encrypted Communication**: GPG key available on request

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if available)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 1 week
- **Fix Timeline**: 30 days for critical, 90 days for others

### Security Measures

This project implements several security measures:

- **Automated Dependency Scanning**: Dependabot monitors for vulnerable dependencies
- **Security Auditing**: OpenSSF Scorecard tracks security best practices
- **Vulnerability Scanning**: Trivy scans for CVEs in artifacts and dependencies
- **Supply Chain Security**: SBOM generation for transparency
- **Code Analysis**: Security-focused linting and analysis

### Disclosure Policy

- We follow responsible disclosure practices
- Security fixes are prioritized and released promptly
- Public disclosure occurs after fixes are available
- Security advisories are published for significant vulnerabilities

### Security Best Practices

When using dev-box:

1. **Keep Updated**: Always use the latest supported version
2. **Network Security**: Use private networks for development VMs
3. **Host Security**: Keep your host system updated and secure
4. **Credential Management**: Never commit secrets or credentials
5. **VM Isolation**: Use snapshots and proper VM isolation

## Security Contact

For urgent security matters, contact the maintainers directly through:
- GitHub Security Advisory (preferred)
- Project maintainer emails (see MAINTAINERS.md)

Thank you for helping keep dev-box secure!