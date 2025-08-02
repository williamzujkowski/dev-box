"""
Security utilities for safe file operations and data handling.

This module provides secure alternatives to potentially dangerous operations
like tar extraction and pickle deserialization.
"""

import hashlib
import hmac
import json
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from typing import Union

logger = logging.getLogger(__name__)


class SecureTarExtractor:
    """Secure tar file extraction with path traversal protection."""

    def __init__(self, max_size: int = 100 * 1024 * 1024):  # 100MB default
        """
        Initialize secure tar extractor.

        Args:
            max_size: Maximum allowed extracted size in bytes
        """
        self.max_size = max_size
        self.extracted_size = 0

    def is_safe_path(self, path: str, base_path: Path) -> bool:
        """
        Check if extraction path is safe (no directory traversal).

        Args:
            path: Path to check
            base_path: Base extraction directory

        Returns:
            True if path is safe, False otherwise
        """
        # Normalize the path and resolve any symlinks
        try:
            normalized_path = Path(path).resolve()
            base_resolved = base_path.resolve()

            # Check if the normalized path is within the base path
            return str(normalized_path).startswith(str(base_resolved))
        except (OSError, ValueError):
            return False

    def safe_extract_member(
        self, tar: tarfile.TarFile, member: tarfile.TarInfo, extract_path: Path
    ) -> bool:
        """
        Safely extract a single tar member with security checks.

        Args:
            tar: Open tar file object
            member: Tar member to extract
            extract_path: Base extraction path

        Returns:
            True if extraction was successful, False if blocked
        """
        # Security checks
        if member.isdev():
            logger.warning(f"Blocked device file: {member.name}")
            return False

        if member.issym() or member.islnk():
            logger.warning(f"Blocked symbolic/hard link: {member.name}")
            return False

        # Check for absolute paths
        if os.path.isabs(member.name):
            logger.warning(f"Blocked absolute path: {member.name}")
            return False

        # Check for path traversal
        target_path = extract_path / member.name
        if not self.is_safe_path(target_path, extract_path):
            logger.warning(f"Blocked path traversal attempt: {member.name}")
            return False

        # Check file size limits
        if member.size > self.max_size:
            logger.warning(f"File too large: {member.name} ({member.size} bytes)")
            return False

        if self.extracted_size + member.size > self.max_size:
            logger.warning("Total extraction size limit exceeded")
            return False

        try:
            # Safe extraction
            tar.extract(member, path=extract_path)
            self.extracted_size += member.size
            return True
        except Exception as e:
            logger.error(f"Failed to extract {member.name}: {e}")
            return False

    def safe_extractall(
        self, tar_path: Union[str, Path], extract_path: Union[str, Path]
    ) -> List[str]:
        """
        Safely extract all members from a tar file.

        Args:
            tar_path: Path to tar file
            extract_path: Directory to extract to

        Returns:
            List of successfully extracted file paths

        Raises:
            ValueError: If tar file or extraction path is invalid
            SecurityError: If malicious content is detected
        """
        tar_path = Path(tar_path)
        extract_path = Path(extract_path)

        if not tar_path.exists():
            raise ValueError(f"Tar file does not exist: {tar_path}")

        # Ensure extraction directory exists
        extract_path.mkdir(parents=True, exist_ok=True)

        extracted_files = []
        self.extracted_size = 0

        try:
            with tarfile.open(tar_path, "r:*") as tar:
                # Get all members first for validation
                members = tar.getmembers()

                # Check total uncompressed size
                total_size = sum(member.size for member in members if member.isfile())
                if total_size > self.max_size:
                    raise SecurityError(f"Archive too large: {total_size} bytes")

                # Extract each member safely
                for member in members:
                    if member.isfile():
                        if self.safe_extract_member(tar, member, extract_path):
                            extracted_files.append(str(extract_path / member.name))
                        else:
                            logger.warning(f"Skipped unsafe member: {member.name}")

        except tarfile.TarError as e:
            raise ValueError(f"Invalid tar file: {e}")

        return extracted_files


class SecureSerializer:
    """Secure serialization using HMAC-signed JSON instead of pickle."""

    def __init__(self, secret_key: Optional[bytes] = None):
        """
        Initialize secure serializer.

        Args:
            secret_key: Secret key for HMAC signing. If None, a random key is generated.
        """
        if secret_key is None:
            secret_key = os.urandom(32)
        self.secret_key = secret_key

    def _generate_signature(self, data: str) -> str:
        """Generate HMAC signature for data."""
        return hmac.new(
            self.secret_key, data.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, data: str, signature: str) -> bool:
        """Verify HMAC signature for data."""
        expected_signature = self._generate_signature(data)
        return hmac.compare_digest(expected_signature, signature)

    def serialize(self, obj: Any) -> str:
        """
        Securely serialize object to signed JSON.

        Args:
            obj: Object to serialize

        Returns:
            Signed JSON string
        """
        try:
            # Convert to JSON-serializable format
            json_data = self._make_json_serializable(obj)
            json_str = json.dumps(json_data, separators=(",", ":"), sort_keys=True)

            # Generate signature
            signature = self._generate_signature(json_str)

            # Create signed package
            signed_data = {
                "data": json_str,
                "signature": signature,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return json.dumps(signed_data)

        except Exception as e:
            raise ValueError(f"Serialization failed: {e}")

    def deserialize(self, signed_data: str) -> Any:
        """
        Securely deserialize signed JSON.

        Args:
            signed_data: Signed JSON string

        Returns:
            Deserialized object

        Raises:
            ValueError: If data is invalid or signature verification fails
        """
        try:
            # Parse signed package
            package = json.loads(signed_data)
            data = package["data"]
            signature = package["signature"]

            # Verify signature
            if not self._verify_signature(data, signature):
                raise ValueError("Signature verification failed - data may be tampered")

            # Deserialize data
            json_obj = json.loads(data)
            return self._restore_from_json(json_obj)

        except KeyError as e:
            raise ValueError(f"Invalid signed data format: missing {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")
        except Exception as e:
            raise ValueError(f"Deserialization failed: {e}")

    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {
                str(key): self._make_json_serializable(value)
                for key, value in obj.items()
            }
        if isinstance(obj, datetime):
            return {"_type": "datetime", "_value": obj.isoformat()}
        if isinstance(obj, Path):
            return {"_type": "path", "_value": str(obj)}
        if hasattr(obj, "__dict__"):
            return {
                "_type": "object",
                "_class": obj.__class__.__name__,
                "_data": self._make_json_serializable(obj.__dict__),
            }
        # Fallback to string representation
        return {"_type": "string_repr", "_value": str(obj)}

    def _restore_from_json(self, obj: Any) -> Any:
        """Restore object from JSON-serializable format."""
        if isinstance(obj, dict) and "_type" in obj:
            obj_type = obj["_type"]
            if obj_type == "datetime":
                return datetime.fromisoformat(obj["_value"])
            if obj_type == "path":
                return Path(obj["_value"])
            if obj_type == "string_repr":
                return obj["_value"]
            if obj_type == "object":
                # Simple object reconstruction - may need enhancement
                return obj["_data"]
        elif isinstance(obj, dict):
            return {key: self._restore_from_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._restore_from_json(item) for item in obj]
        else:
            return obj


class SecurityError(Exception):
    """Custom exception for security-related errors."""


def get_secure_temp_dir() -> Path:
    """Get a secure temporary directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="secure_"))
    # Set restrictive permissions
    temp_dir.chmod(0o700)
    return temp_dir


def validate_file_path(
    file_path: Union[str, Path], base_path: Union[str, Path]
) -> bool:
    """
    Validate that a file path is within the allowed base path.

    Args:
        file_path: Path to validate
        base_path: Base allowed path

    Returns:
        True if path is valid, False otherwise
    """
    try:
        file_path = Path(file_path).resolve()
        base_path = Path(base_path).resolve()
        return str(file_path).startswith(str(base_path))
    except (OSError, ValueError):
        return False
