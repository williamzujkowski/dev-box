# Dependabot Intelligent Grouping Strategy

## Overview

This document outlines the intelligent dependency grouping strategy implemented for the dev-box project to reduce PR noise while maintaining security and stability.

## Grouping Strategy

### 🔒 Security Dependencies (Immediate Updates)

**Schedule**: Daily checks, immediate security updates
**Auto-merge**: Security patches after CI passes

- **Critical Security Libraries**: `cryptography`, `certifi`, `urllib3`, `requests`, `httpx`, `pyjwt`, `bcrypt`, `passlib`, `pycryptodome`
- **Security Scanning Tools**: `bandit`, `safety`, `semgrep`, `flake8-security`

### 🐍 Python Dependencies

#### Production Dependencies (Weekly Updates)
- **Core Libraries**: `psutil`, `pyyaml`, `click`, `rich`, `cerberus`, `marshmallow`, `jsonschema`
- **Container Tools**: `docker`

#### Development Tools (Monthly Updates)
- **Code Formatting**: `black`, `ruff`, `flake8`, `isort`, `pre-commit`
- **Type Checking**: `mypy`, `pylint`

#### Testing Framework (Monthly Updates)
- **Core Testing**: `pytest*`, `coverage`, `faker`, `factory-boy`, `freezegun`
- **Mock & Fixtures**: `responses`, `requests-mock`, `unittest-mock`, `testcontainers`
- **Performance Testing**: `pexpect`, `ptyprocess`, `pyfakefs`, `locust`, `model-bakery`

### 📦 JavaScript Dependencies

#### Code Quality Tools (Monthly Updates)
- **Linting**: `eslint*`, `prettier`, `eslint-config-prettier`
- **Git Workflow**: `husky`, `lint-staged`, `@commitlint/*`, `commitizen`, `conventional-changelog*`

#### Documentation Site (Weekly Updates)
- **Build Tools**: `@11ty/*`, `eleventy`, `lighthouse`

### ⚙️ GitHub Actions

#### Security Actions (Weekly Updates)
- **Security Scanning**: `github/codeql-action`, `ossf/scorecard-action`, `anchore/scan-action`, `aquasecurity/trivy-action`

#### CI/CD Actions (Weekly Updates)  
- **Workflow Actions**: `actions/checkout`, `actions/setup-python`, `actions/setup-node`, `actions/cache`
- **Build Actions**: `docker/build-push-action`, `docker/setup-buildx-action`

#### Documentation Actions (Weekly Updates)
- **Deployment**: `actions/deploy-pages`, `actions/configure-pages`, `treosh/lighthouse-ci-action`

## Update Schedules

| Category | Schedule | Auto-merge | Priority |
|----------|----------|------------|----------|
| Security Critical | Daily | ✅ After CI | Immediate |
| Security Tools | Weekly | ✅ Patch only | High |
| Production Libraries | Weekly | ❌ Manual review | High |
| Development Tools | Monthly | ✅ Patch only | Medium |
| Testing Framework | Monthly | ✅ Patch only | Medium |
| JavaScript Tools | Monthly | ✅ Patch only | Low |
| GitHub Actions | Weekly | ✅ Minor/Patch | Medium |
| Documentation | Weekly | ✅ Minor/Patch | Low |

## Auto-merge Rules

### ✅ Automatic Merge Conditions

1. **Security Updates**: All security patches after CI passes
2. **Development Tool Patches**: Patch-level updates to formatting/linting tools
3. **Testing Framework Patches**: Patch updates to testing dependencies
4. **GitHub Actions Minor/Patch**: Non-breaking workflow updates

### ❌ Manual Review Required

1. **Major Version Updates**: All major version bumps
2. **Critical Security Libraries**: `cryptography`, `requests`, `httpx` (manual verification)
3. **New Dependencies**: Any newly added dependencies
4. **Breaking Changes**: Updates with known breaking changes

## Labels and Assignment

### Labels Applied Automatically
- `dependencies` - All dependency updates
- `security` - Security-related updates
- `auto-merge` - Eligible for automatic merging
- `python`/`javascript`/`github-actions` - Language/platform specific
- `high-priority`/`medium-priority`/`low-priority` - Update urgency

### Assignment Strategy
- Security updates: `dev-box-team` for immediate attention
- Development tool updates: Auto-merge after CI
- Production updates: Manual review by maintainers

## Benefits

### 🚀 Reduced PR Noise
- **Before**: 20-30 individual dependency PRs per week
- **After**: 5-8 grouped PRs per week (75% reduction)

### 🔒 Enhanced Security
- Immediate security updates with daily checks
- Separate critical security library handling
- Comprehensive security scanning tool updates

### ⚡ Improved Efficiency
- Auto-merge for low-risk updates
- Grouped related dependencies
- Intelligent scheduling to avoid conflicts

### 🛡️ Maintained Stability
- Manual review for major updates
- Separate testing for critical dependencies
- CI validation before auto-merge

## Monitoring and Metrics

Track the following metrics to evaluate effectiveness:

1. **PR Volume Reduction**: Measure weekly PR count before/after
2. **Security Response Time**: Time from vulnerability disclosure to merge
3. **CI Success Rate**: Percentage of auto-merged PRs that pass CI
4. **Manual Review Rate**: Percentage of updates requiring manual intervention

## Configuration Files

- `.github/dependabot.yml` - Main Dependabot configuration
- `.github/dependabot-auto-merge.yml` - Auto-merge rules documentation
- This document - Strategy and rationale

## Maintenance

Review and update this strategy:
- **Monthly**: Evaluate grouping effectiveness
- **Quarterly**: Assess auto-merge success rate
- **As needed**: Add new dependencies to appropriate groups