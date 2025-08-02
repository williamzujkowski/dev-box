"""
Serialization utilities for state management

Provides secure and efficient serialization/deserialization for sandbox state data.
"""

import json
import pickle
import logging
from typing import Any, Optional, Dict, Union
from dataclasses import is_dataclass, asdict
from datetime import datetime
import base64


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
            elif format_type == "pickle":
                return await self._serialize_pickle(data)
            else:
                raise ValueError(f"Unsupported serialization format: {format_type}")
                
        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
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
            elif format_type == "pickle":
                return await self._deserialize_pickle(data)
            else:
                raise ValueError(f"Unsupported deserialization format: {format_type}")
                
        except Exception as e:
            self.logger.error(f"Deserialization failed: {e}")
            raise
    
    async def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string"""
        try:
            # Handle special types
            serializable_data = await self._make_json_serializable(data)
            return json.dumps(serializable_data, indent=None, separators=(',', ':'))
        except Exception as e:
            raise ValueError(f"JSON serialization failed: {e}")
    
    async def _deserialize_json(self, data: str) -> Any:
        """Deserialize JSON string to data"""
        try:
            return json.loads(data)
        except Exception as e:
            raise ValueError(f"JSON deserialization failed: {e}")
    
    async def _serialize_pickle(self, data: Any) -> str:
        """Serialize data to base64-encoded pickle string"""
        try:
            # Note: Pickle should only be used for trusted data
            pickled_data = pickle.dumps(data)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            return encoded_data
        except Exception as e:
            raise ValueError(f"Pickle serialization failed: {e}")
    
    async def _deserialize_pickle(self, data: str) -> Any:
        """Deserialize base64-encoded pickle string to data"""
        try:
            # Security warning: Only deserialize trusted pickle data
            decoded_data = base64.b64decode(data.encode('utf-8'))
            return pickle.loads(decoded_data)
        except Exception as e:
            raise ValueError(f"Pickle deserialization failed: {e}")
    
    async def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [await self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {
                str(key): await self._make_json_serializable(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, datetime):
            return {
                "_type": "datetime",
                "_value": obj.isoformat()
            }
        elif is_dataclass(obj):
            return {
                "_type": "dataclass",
                "_class": obj.__class__.__name__,
                "_value": await self._make_json_serializable(asdict(obj))
            }
        elif hasattr(obj, '__dict__'):
            return {
                "_type": "object",
                "_class": obj.__class__.__name__,
                "_value": await self._make_json_serializable(obj.__dict__)
            }
        else:
            # Fallback to string representation
            return {
                "_type": "string_repr",
                "_value": str(obj)
            }


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
        logger.error(f"Storage serialization failed: {e}")
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
        logger.error(f"Storage deserialization failed: {e}")
        return None