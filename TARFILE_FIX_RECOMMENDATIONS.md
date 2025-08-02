# Tarfile Security Fix Recommendations

## Files requiring review:

./sandbox-core/src/sandbox/lifecycle/initializer.py
./sandbox-core/src/sandbox/utils/security.py
./sandbox-core/src/sandbox/safety/rollback.py ./sandbox-core/security_scan.py
./sandbox-core/tests/test_security_fixes.py ./src/safe_extract.py

## How to fix:

Replace unsafe usage:

```python
# UNSAFE (CVE-2025-4517)
import tarfile
with tarfile.open('file.tar') as tar:
    tar.extractall('/path')  # VULNERABLE!

# SAFE
from src.safe_extract import safe_extractall
safe_extractall('file.tar', '/path')
```

## Manual review required for each file listed above.
