"""
Secure serialization alternatives to pickle.
Addresses CWE-502 pickle deserialization vulnerabilities.
"""

import json
import hmac
import hashlib
from typing import Any, Optional


class SecureSerializer:
    """Secure alternative to pickle with HMAC signing."""
    
    def __init__(self, secret_key: str):
        """Initialize with secret key for HMAC signing."""
        self.secret_key = secret_key.encode()
    
    def _sign_data(self, data: str) -> str:
        """Create HMAC signature for data."""
        signature = hmac.new(
            self.secret_key, 
            data.encode(), 
            hashlib.sha256
        ).hexdigest()
        return f"{signature}:{data}"
    
    def _verify_data(self, signed_data: str) -> Optional[str]:
        """Verify HMAC signature and return data."""
        try:
            signature, data = signed_data.split(':', 1)
            expected_signature = hmac.new(
                self.secret_key, 
                data.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                return data
            return None
        except ValueError:
            return None
    
    def serialize(self, obj: Any) -> str:
        """Serialize object to signed JSON."""
        json_data = json.dumps(obj, default=str)
        return self._sign_data(json_data)
    
    def deserialize(self, signed_data: str) -> Optional[Any]:
        """Deserialize signed JSON to object."""
        data = self._verify_data(signed_data)
        if data is None:
            return None
        
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None


# Migration helpers
def safe_dumps(obj: Any, secret_key: str) -> str:
    """Secure replacement for pickle.dumps()."""
    serializer = SecureSerializer(secret_key)
    return serializer.serialize(obj)


def safe_loads(data: str, secret_key: str) -> Optional[Any]:
    """Secure replacement for pickle.loads()."""
    serializer = SecureSerializer(secret_key)
    return serializer.deserialize(data)


# Example usage
if __name__ == "__main__":
    # BEFORE (UNSAFE):
    # import pickle
    # data = pickle.dumps(obj)        # VULNERABLE!
    # obj = pickle.loads(data)        # VULNERABLE!
    
    # AFTER (SAFE):
    secret = "your-secret-key-here"  # Use environment variable in production
    
    obj = {"test": "data", "number": 42}
    serialized = safe_dumps(obj, secret)
    deserialized = safe_loads(serialized, secret)
    
    print(f"✅ Secure serialization: {deserialized}")
