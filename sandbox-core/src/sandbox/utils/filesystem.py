"""
Filesystem utilities for safe file operations

Provides secure filesystem operations with proper error handling,
permission management, and path validation.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Union, Optional, List
import stat
import shutil


logger = logging.getLogger(__name__)


async def safe_mkdir(path: Union[str, Path], mode: int = 0o755, parents: bool = True, 
                    exist_ok: bool = True) -> bool:
    """
    Safely create directory with proper permissions
    
    Args:
        path: Directory path to create
        mode: Directory permissions
        parents: Create parent directories if needed
        exist_ok: Don't raise error if directory exists
        
    Returns:
        bool: True if successful
    """
    try:
        path = Path(path)
        path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


async def safe_chmod(path: Union[str, Path], mode: int) -> bool:
    """
    Safely change file/directory permissions
    
    Args:
        path: Path to modify
        mode: New permissions
        
    Returns:
        bool: True if successful
    """
    try:
        path = Path(path)
        path.chmod(mode)
        return True
    except Exception as e:
        logger.error(f"Failed to change permissions for {path}: {e}")
        return False


def validate_path(path: Union[str, Path]) -> bool:
    """
    Validate path for security and correctness
    
    Args:
        path: Path to validate
        
    Returns:
        bool: True if path is valid and safe
    """
    try:
        path = Path(path)
        
        # Check for path traversal attempts
        if ".." in str(path):
            return False
        
        # Check for absolute paths outside allowed areas
        if path.is_absolute():
            # Allow only paths within common safe directories
            safe_prefixes = ["/tmp", "/var/tmp", "/home", "/opt"]
            if not any(str(path).startswith(prefix) for prefix in safe_prefixes):
                return False
        
        return True
        
    except Exception:
        return False


class FilesystemChecker:
    """Filesystem health and accessibility checker"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FilesystemChecker")
    
    async def check_accessibility(self, path: Union[str, Path]) -> bool:
        """
        Check if path is accessible for read/write operations
        
        Args:
            path: Path to check
            
        Returns:
            bool: True if accessible
        """
        try:
            path = Path(path)
            
            if not path.exists():
                return False
            
            # Check read permission
            if not os.access(path, os.R_OK):
                return False
            
            # Check write permission
            if not os.access(path, os.W_OK):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check accessibility for {path}: {e}")
            return False
    
    async def get_disk_usage(self, path: Union[str, Path]) -> dict:
        """
        Get disk usage information for path
        
        Args:
            path: Path to check
            
        Returns:
            dict: Disk usage information
        """
        try:
            usage = shutil.disk_usage(path)
            return {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "usage_percent": (usage.used / usage.total) * 100
            }
        except Exception as e:
            self.logger.error(f"Failed to get disk usage for {path}: {e}")
            return {}
    
    async def check_permissions(self, path: Union[str, Path]) -> dict:
        """
        Check file/directory permissions
        
        Args:
            path: Path to check
            
        Returns:
            dict: Permission information
        """
        try:
            path = Path(path)
            if not path.exists():
                return {}
            
            st = path.stat()
            mode = st.st_mode
            
            return {
                "mode": oct(mode),
                "readable": os.access(path, os.R_OK),
                "writable": os.access(path, os.W_OK),
                "executable": os.access(path, os.X_OK),
                "owner_read": bool(mode & stat.S_IRUSR),
                "owner_write": bool(mode & stat.S_IWUSR),
                "owner_execute": bool(mode & stat.S_IXUSR),
                "group_read": bool(mode & stat.S_IRGRP),
                "group_write": bool(mode & stat.S_IWGRP),
                "group_execute": bool(mode & stat.S_IXGRP),
                "other_read": bool(mode & stat.S_IROTH),
                "other_write": bool(mode & stat.S_IWOTH),
                "other_execute": bool(mode & stat.S_IXOTH)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to check permissions for {path}: {e}")
            return {}