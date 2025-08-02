"""
Safe tarfile extraction wrapper to prevent path traversal attacks.
Addresses CVE-2025-4517 and implements secure extraction practices.
"""

import os
import tarfile
from pathlib import Path
from typing import Optional, Union


class SafeTarExtractor:
    """Safe tarfile extraction with path validation and security checks."""
    
    def __init__(self, base_path: Union[str, Path]):
        """Initialize with base extraction path."""
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _is_safe_path(self, member_path: str) -> bool:
        """Validate that extraction path is safe."""
        # Resolve the target path
        target_path = (self.base_path / member_path).resolve()
        
        # Check if target is within base directory
        try:
            target_path.relative_to(self.base_path)
            return True
        except ValueError:
            return False
    
    def _sanitize_member(self, member: tarfile.TarInfo) -> Optional[tarfile.TarInfo]:
        """Sanitize tar member for safe extraction."""
        # Reject absolute paths
        if member.name.startswith('/'):
            return None
        
        # Reject paths with parent directory references
        if '..' in member.name.split('/'):
            return None
        
        # Reject device files, links, etc.
        if not (member.isfile() or member.isdir()):
            return None
        
        # Validate the final path is safe
        if not self._is_safe_path(member.name):
            return None
        
        return member
    
    def safe_extract(self, tar_path: Union[str, Path], 
                    extract_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Safely extract tarfile with security validation.
        
        Args:
            tar_path: Path to tar file
            extract_path: Optional specific extraction path
            
        Returns:
            bool: True if extraction successful, False otherwise
        """
        if extract_path:
            extract_target = Path(extract_path).resolve()
        else:
            extract_target = self.base_path
        
        try:
            with tarfile.open(tar_path, 'r') as tar:
                for member in tar:
                    # Sanitize each member
                    safe_member = self._sanitize_member(member)
                    if safe_member is None:
                        print(f"Skipping unsafe member: {member.name}")
                        continue
                    
                    # Extract individual member safely
                    tar.extract(safe_member, extract_target)
            
            return True
            
        except (tarfile.TarError, OSError, ValueError) as e:
            print(f"Extraction failed: {e}")
            return False


def safe_extractall(tar_path: Union[str, Path], 
                   extract_path: Union[str, Path]) -> bool:
    """
    Drop-in replacement for tarfile.extractall() with security.
    
    Usage:
        # Instead of: tar.extractall(path)
        # Use: safe_extractall(tar_file, path)
    """
    extractor = SafeTarExtractor(extract_path)
    return extractor.safe_extract(tar_path)


# Example usage and migration guide
if __name__ == "__main__":
    # BEFORE (UNSAFE):
    # with tarfile.open('archive.tar.gz', 'r:gz') as tar:
    #     tar.extractall('/tmp/extract')  # VULNERABLE!
    
    # AFTER (SAFE):
    extractor = SafeTarExtractor('/tmp/extract')
    success = extractor.safe_extract('archive.tar.gz')
    
    if success:
        print("✅ Safe extraction completed")
    else:
        print("❌ Extraction failed or blocked unsafe content")
