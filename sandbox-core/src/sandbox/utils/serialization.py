"""
Serialization utilities for state management

Provides secure and efficient serialization/deserialization for sandbox state data.
"""

import base64
import json
import logging
import pickle
from dataclasses import asdict
from dataclasses import is_dataclass
from datetime import datetime
from typing import Any
from typing import Optional

from .security import SecureSerializer

logger = logging.getLogger(__name__)


class StateSerializer:
    """
    Safe serialization for sandbox state data

    Supports JSON and pickle formats with security considerations
    """

    def __init__(self, default_format: str = "json"):
        self.default_format = default_format
        self.logger = logging.getLogger(f"{__name__}.StateSerializer")

    async def serialize(self, data: Any, format_type: Optional[str] = None) -> str:
        """
        Serialize data to string format

        Args:
            data: Data to serialize
            format_type: Serialization format (json, pickle)

        Returns:
            str: Serialized data
        """
        try:
            format_type = format_type or self.default_format

            if format_type == "json":
                return await self._serialize_json(data)
            if format_type == "pickle":
                return await self._serialize_pickle(data)
            raise ValueError(f"Unsupported serialization format: {format_type}")

        except Exception as e:
            self.logger.exception(f"Serialization failed: {e}")
            raise

    async def deserialize(self, data: str, format_type: Optional[str] = None) -> Any:
        """
        Deserialize string data back to original format

        Args:
            data: Serialized data string
            format_type: Expected format (json, pickle)

        Returns:
            Any: Deserialized data
        """
        try:
            format_type = format_type or self.default_format

            if format_type == "json":
                return await self._deserialize_json(data)
            if format_type == "pickle":
                return await self._deserialize_pickle(data)
            raise ValueError(f"Unsupported deserialization format: {format_type}")

        except Exception as e:
            self.logger.exception(f"Deserialization failed: {e}")
            raise

    async def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string"""
        try:
            # Handle special types
            serializable_data = await self._make_json_serializable(data)
            return json.dumps(serializable_data, indent=None, separators=(",", ":"))
        except Exception as e:
            raise ValueError(f"JSON serialization failed: {e}")

    async def _deserialize_json(self, data: str) -> Any:
        """Deserialize JSON string to data"""
        try:
            return json.loads(data)
        except Exception as e:
            raise ValueError(f"JSON deserialization failed: {e}")

    async def _serialize_pickle(self, data: Any) -> str:
        """
        DEPRECATED: Use secure serialization instead of pickle.
        This method is kept for backward compatibility but will be removed.
        """
        logger.warning(
            "Using deprecated pickle serialization. Consider migrating to secure serialization."
        )

        # Use secure serialization instead of pickle
        secure_serializer = SecureSerializer()
        try:
            return secure_serializer.serialize(data)
        except Exception as e:
            # Fallback to pickle only for backward compatibility
            logger.exception(
                f"Secure serialization failed, falling back to pickle: {e}"
            )
            try:
                # Note: Pickle should only be used for trusted data
                pickled_data = pickle.dumps(data)
                return base64.b64encode(pickled_data).decode("utf-8")
            except Exception as pickle_error:
                raise ValueError(
                    f"Both secure and pickle serialization failed: {pickle_error}"
                )

    async def _deserialize_pickle(self, data: str) -> Any:
        """
        DEPRECATED: Use secure deserialization instead of pickle.
        This method attempts secure deserialization first, with pickle fallback.
        """
        logger.warning(
            "Using deprecated pickle deserialization. Consider migrating to secure deserialization."
        )

        # Try secure deserialization first
        secure_serializer = SecureSerializer()
        try:
            return secure_serializer.deserialize(data)
        except Exception:
            # Security: Removed pickle fallback (fixes CWE-502)
            # Use secure JSON serialization instead of pickle for all data
            logger.exception(
                "Secure deserialization failed - pickle fallback disabled for security"
            )
            raise ValueError(
                "Deserialization failed: only secure JSON format supported"
            )

    async def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [await self._make_json_serializable(item) for item in obj]
        if isinstance(obj, dict):
            return {
                str(key): await self._make_json_serializable(value)
                for key, value in obj.items()
            }
        if isinstance(obj, datetime):
            return {"_type": "datetime", "_value": obj.isoformat()}
        if is_dataclass(obj):
            return {
                "_type": "dataclass",
                "_class": obj.__class__.__name__,
                "_value": await self._make_json_serializable(asdict(obj)),
            }
        if hasattr(obj, "__dict__"):
            return {
                "_type": "object",
                "_class": obj.__class__.__name__,
                "_value": await self._make_json_serializable(obj.__dict__),
            }
        # Fallback to string representation
        return {"_type": "string_repr", "_value": str(obj)}


def serialize_for_storage(data: Any) -> str:
    """
    Convenience function for serializing data for storage

    Args:
        data: Data to serialize

    Returns:
        str: JSON-serialized data
    """
    serializer = StateSerializer("json")
    try:
        import asyncio

        return asyncio.run(serializer.serialize(data))
    except Exception as e:
        logger.exception(f"Storage serialization failed: {e}")
        return "{}"


def deserialize_from_storage(data: str) -> Any:
    """
    Convenience function for deserializing data from storage

    Args:
        data: Serialized data string

    Returns:
        Any: Deserialized data
    """
    serializer = StateSerializer("json")
    try:
        import asyncio

        return asyncio.run(serializer.deserialize(data))
    except Exception as e:
        logger.exception(f"Storage deserialization failed: {e}")
        return None
