# 🎨 Code Style Guide

This document outlines the coding standards and style guidelines for the dev-box
project.

## 📋 Overview

We maintain consistent code style across all languages using automated tools and
pre-commit hooks:

- **Python**: Black + Ruff (PEP 8 compliant)
- **JavaScript/TypeScript**: Prettier + ESLint
- **Shell Scripts**: Basic formatting with consistent indentation
- **Configuration Files**: Consistent formatting and validation

## 🐍 Python Style Guidelines

### Formatting (Black)

- **Line Length**: 88 characters (Black default)
- **Quotes**: Double quotes preferred
- **Indentation**: 4 spaces

### Linting (Ruff)

- **Import Sorting**: isort-compatible, single-line imports
- **Code Quality**: Comprehensive rule set covering:
  - Pycodestyle (E, W)
  - Pyflakes (F)
  - Import conventions (I)
  - Naming conventions (N)
  - Bugbear (B)
  - Flake8 extensions

### Example

```python
"""Module docstring with description."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from typing import Dict

from ..utils.security import SafeTarExtractor


class ExampleClass:
    """Class docstring."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def process_data(self, data: Any) -> Dict[str, Any]:
        """Process data asynchronously."""
        try:
            result = await self._process_impl(data)
            return {"success": True, "result": result}
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            return {"success": False, "error": str(e)}
```

## 🟨 JavaScript/TypeScript Style Guidelines

### Formatting (Prettier)

- **Line Length**: 88 characters (consistent with Python)
- **Quotes**: Double quotes
- **Semicolons**: Always include
- **Trailing Commas**: ES5 compatible
- **Indentation**: 2 spaces

### Linting (ESLint)

- **Best Practices**: No unused variables, prefer const/let
- **Quality Rules**: Strict equality, curly braces, no eval
- **Modern Features**: Template literals, arrow functions

### Example

```javascript
const { EleventyNavigationPlugin } = require("@11ty/eleventy-navigation");

module.exports = function (eleventyConfig) {
  // Add plugins
  eleventyConfig.addPlugin(EleventyNavigationPlugin);

  // Add custom filters
  eleventyConfig.addFilter("dateDisplay", function (dateObj) {
    return new Date(dateObj).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  });

  return {
    dir: {
      input: "src",
      output: "_site",
    },
  };
};
```

## 🐚 Shell Script Guidelines

### Basic Standards

- **Indentation**: 2 spaces
- **Shebang**: `#!/bin/bash`
- **Error Handling**: Use `set -e` for strict error handling
- **Quoting**: Quote variables to prevent word splitting

### Example

```bash
#!/bin/bash
# Script description

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log() {
  echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
  echo -e "${GREEN}✅ $1${NC}"
}

# Main execution
if [ "$EUID" -eq 0 ]; then
  log "Starting configuration..."
  success "Configuration complete"
fi
```

## 📝 Configuration Files

### JSON

- **Indentation**: 2 spaces
- **Validation**: Proper JSON syntax
- **Formatting**: Consistent key ordering where possible

### YAML

- **Indentation**: 2 spaces
- **Line Endings**: LF (Unix-style)
- **Validation**: Proper YAML syntax

### TOML

- **Formatting**: Standard TOML conventions
- **Validation**: Proper syntax checking

## 🛠️ Development Workflow

### Pre-commit Hooks

All code is automatically formatted and validated on commit:

```bash
# Install hooks (one-time setup)
pre-commit install

# Run on all files manually
pre-commit run --all-files

# Skip hooks (emergency only)
git commit --no-verify
```

### Manual Formatting

```bash
# Format Python files
black .
ruff check --fix .
ruff format .

# Format JavaScript/TypeScript
npx prettier --write "**/*.{js,jsx,ts,tsx,json,md,yaml,yml}"
npx eslint . --ext .js,.jsx,.ts,.tsx --fix

# Check all formatting
npm run format:check
```

### Validation Scripts

```bash
# Run style checks
npm run lint

# Run full formatting
npm run format

# Check formatting without changes
npm run style:check
```

## 🚫 Common Anti-patterns

### Python

❌ **Avoid:**

```python
# Poor formatting
def bad_function(x,y,z):
    if x>y:return z
    else:return x+y

# Poor imports
from module import *
import sys,os,json
```

✅ **Prefer:**

```python
# Good formatting
def good_function(x: int, y: int, z: int) -> int:
    if x > y:
        return z
    return x + y

# Good imports
import json
import os
import sys
```

### JavaScript

❌ **Avoid:**

```javascript
// Poor formatting
function badFunction(x, y) {
  if (x > y) return y;
  else return x;
}

// Poor practices
var data = getData();
if (data == null) {
  // handle error
}
```

✅ **Prefer:**

```javascript
// Good formatting
function goodFunction(x, y) {
  if (x > y) {
    return y;
  }
  return x;
}

// Good practices
const data = getData();
if (data === null) {
  // handle error
}
```

## 🔧 Tool Configuration

### pyproject.toml

```toml
[tool.black]
line-length = 88
target-version = ['py39']

[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "W", "I", "N", "UP", "B"]
ignore = ["E501", "E203"]
```

### .prettierrc

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": false,
  "printWidth": 88,
  "tabWidth": 2,
  "useTabs": false
}
```

### .eslintrc.js

```javascript
module.exports = {
  env: {
    node: true,
    es2021: true,
  },
  extends: ["eslint:recommended", "prettier"],
  rules: {
    "no-console": "warn",
    "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "prefer-const": "error",
    eqeqeq: ["error", "always"],
  },
};
```

## 📊 Style Violation Summary

### Current Status

As of the style cleanup implementation:

- **Python Files**: 27 files reformatted with Black
- **Ruff Issues**: 838 issues found (168 fixed automatically)
- **JavaScript/TypeScript**: Multiple files formatted with Prettier
- **Configuration Files**: Standardized formatting applied

### Priority Issues

1. **High Priority**: Security-related linting issues
2. **Medium Priority**: Code complexity and maintainability
3. **Low Priority**: Style consistency and documentation

## 🎯 Continuous Improvement

### Metrics Tracking

- **Pre-commit Success Rate**: Track hook execution success
- **Style Violation Trends**: Monitor reduction over time
- **Code Quality Metrics**: Complexity, coverage, maintainability

### Regular Maintenance

- **Weekly**: Review and address new style violations
- **Monthly**: Update tool configurations and dependencies
- **Quarterly**: Review and refine style guidelines

## 📚 Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Prettier Documentation](https://prettier.io/docs/)
- [ESLint Documentation](https://eslint.org/docs/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

_This style guide is enforced automatically through pre-commit hooks and CI/CD
pipelines. For questions or suggestions, please open an issue or submit a pull
request._
