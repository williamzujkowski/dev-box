# Pickle Security Fix Recommendations

## Files requiring review:

./sandbox-core/src/sandbox/utils/security.py
./sandbox-core/src/sandbox/utils/serialization.py
./sandbox-core/security_scan.py
./sandbox-core/tests/test_security_fixes.py

## How to fix:

Replace unsafe usage:
```python
# UNSAFE (CWE-502)
import pickle
data = pickle.loads(untrusted_data)  # VULNERABLE!

# SAFE
from src.secure_serialization import safe_loads
data = safe_loads(signed_data, secret_key)
```

## Manual review required for each file listed above.
