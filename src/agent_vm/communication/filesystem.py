"""virtio-9p filesystem sharing.

This module provides high-level abstractions for sharing filesystems between
host and guest VMs using virtio-9p, enabling code injection and result extraction.

Key Features:
- Async mount/unmount operations
- File read/write with error handling
- Context manager support for automatic cleanup
- Structured logging with NIST ET timestamps
- Type-safe with strict mypy compliance
"""

import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import structlog
from structlog.stdlib import BoundLogger

# NIST Eastern Time (as per ARCHITECTURE.md requirements)
ET = ZoneInfo("America/New_York")

logger = structlog.get_logger()


class FilesystemError(Exception):
    """Filesystem operation error.

    Raised when filesystem operations fail due to I/O errors,
    permission issues, or mount/unmount failures.
    """

    pass


class FilesystemShare:
    """Manages virtio-9p filesystem sharing between host and guest.

    Provides high-level interface for sharing directories and files
    between host and guest VMs using virtio-9p protocol.

    Attributes:
        host_path: Path to host directory to share
        mount_tag: 9p mount tag for guest
        guest_mount_point: Mount point path in guest
        is_mounted: Whether filesystem is currently mounted

    Example:
        >>> async with FilesystemShare(Path("/tmp/share")) as fs:
        ...     await fs.write_file("code.py", b"print('hello')")
        ...     content = await fs.read_file("results.json")
    """

    def __init__(
        self,
        host_path: Path,
        mount_tag: str = "agent_share",
        guest_mount_point: str = "/mnt/agent",
    ) -> None:
        """Initialize filesystem share.

        Args:
            host_path: Path to host directory to share
            mount_tag: 9p mount tag for guest (default: agent_share)
            guest_mount_point: Mount point in guest (default: /mnt/agent)

        Note:
            Creates host_path directory if it doesn't exist.
        """
        self.host_path = host_path
        self.mount_tag = mount_tag
        self.guest_mount_point = guest_mount_point
        self._is_mounted = False

        # Create host directory if needed
        self.host_path.mkdir(parents=True, exist_ok=True)

        # Bind logger with context
        self._logger: BoundLogger = logger.bind(
            host_path=str(host_path),
            mount_tag=mount_tag,
            guest_mount_point=guest_mount_point,
        )

    @property
    def is_mounted(self) -> bool:
        """Check if filesystem is currently mounted.

        Returns:
            True if mounted, False otherwise
        """
        return self._is_mounted

    async def mount(self) -> None:
        """Mount shared filesystem in guest.

        Mounts the host_path directory in the guest VM at guest_mount_point
        using virtio-9p protocol.

        Raises:
            FilesystemError: If mount operation fails

        Note:
            This operation is idempotent - mounting an already-mounted
            filesystem is safe and will be silently ignored.
        """
        if self._is_mounted:
            self._logger.debug(
                "filesystem_already_mounted",
                timestamp=datetime.now(ET).isoformat(),
            )
            return

        try:
            self._logger.info(
                "filesystem_mounting",
                timestamp=datetime.now(ET).isoformat(),
            )

            # Execute mount operation
            await self._execute_mount()

            self._is_mounted = True
            self._logger.info(
                "filesystem_mounted",
                timestamp=datetime.now(ET).isoformat(),
            )

        except Exception as e:
            self._logger.error(
                "filesystem_mount_failed",
                error=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(ET).isoformat(),
            )
            raise FilesystemError(f"Failed to mount filesystem: {e}") from e

    async def unmount(self) -> None:
        """Unmount shared filesystem.

        Cleanly unmounts the shared filesystem from the guest VM.

        Raises:
            FilesystemError: If unmount operation fails

        Note:
            This operation is idempotent - unmounting an already-unmounted
            filesystem is safe and will be silently ignored.
        """
        if not self._is_mounted:
            self._logger.debug(
                "filesystem_not_mounted",
                timestamp=datetime.now(ET).isoformat(),
            )
            return

        try:
            self._logger.info(
                "filesystem_unmounting",
                timestamp=datetime.now(ET).isoformat(),
            )

            # Execute unmount operation
            await self._execute_unmount()

            self._is_mounted = False
            self._logger.info(
                "filesystem_unmounted",
                timestamp=datetime.now(ET).isoformat(),
            )

        except Exception as e:
            self._logger.error(
                "filesystem_unmount_failed",
                error=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(ET).isoformat(),
            )
            raise FilesystemError(f"Failed to unmount filesystem: {e}") from e

    async def write_file(self, path: str, content: bytes) -> None:
        """Write file to shared filesystem.

        Writes content to the specified path within the shared filesystem.
        Creates parent directories as needed.

        Args:
            path: Relative path within shared filesystem
            content: File content as bytes

        Raises:
            FilesystemError: If write operation fails

        Example:
            >>> await fs.write_file("code/agent.py", b"import sys\\nprint('test')")
        """
        try:
            file_path = self.host_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            self._logger.debug(
                "file_writing",
                path=path,
                size=len(content),
                timestamp=datetime.now(ET).isoformat(),
            )

            # Async file write (run in executor to avoid blocking)
            await asyncio.get_event_loop().run_in_executor(None, file_path.write_bytes, content)

            self._logger.info(
                "file_written",
                path=path,
                size=len(content),
                timestamp=datetime.now(ET).isoformat(),
            )

        except Exception as e:
            self._logger.error(
                "file_write_failed",
                path=path,
                error=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(ET).isoformat(),
            )
            raise FilesystemError(f"Failed to write file {path}: {e}") from e

    async def read_file(self, path: str) -> bytes:
        """Read file from shared filesystem.

        Reads content from the specified path within the shared filesystem.

        Args:
            path: Relative path within shared filesystem

        Returns:
            File content as bytes

        Raises:
            FilesystemError: If file doesn't exist or read fails

        Example:
            >>> content = await fs.read_file("output/results.json")
        """
        try:
            file_path = self.host_path / path

            if not file_path.exists():
                raise FilesystemError(f"File not found: {path}")

            self._logger.debug(
                "file_reading",
                path=path,
                timestamp=datetime.now(ET).isoformat(),
            )

            # Async file read (run in executor to avoid blocking)
            content = await asyncio.get_event_loop().run_in_executor(None, file_path.read_bytes)

            self._logger.info(
                "file_read",
                path=path,
                size=len(content),
                timestamp=datetime.now(ET).isoformat(),
            )

            return content

        except FilesystemError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            self._logger.error(
                "file_read_failed",
                path=path,
                error=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(ET).isoformat(),
            )
            raise FilesystemError(f"Failed to read file {path}: {e}") from e

    async def _execute_mount(self) -> None:
        """Execute the actual mount operation.

        This is a stub implementation for unit testing. In production,
        this would execute guest agent commands or libvirt operations.

        Note:
            Override this method or use dependency injection for production.
        """
        # Stub: In production this would execute mount command in guest
        # For now, just simulate a successful mount
        await asyncio.sleep(0)  # Simulate async operation

    async def _execute_unmount(self) -> None:
        """Execute the actual unmount operation.

        This is a stub implementation for unit testing. In production,
        this would execute guest agent commands or libvirt operations.

        Note:
            Override this method or use dependency injection for production.
        """
        # Stub: In production this would execute umount command in guest
        # For now, just simulate a successful unmount
        await asyncio.sleep(0)  # Simulate async operation

    async def cleanup(self) -> None:
        """Clean up filesystem share resources.

        Unmounts filesystem and removes all files from host_path.
        Keeps the host_path directory itself.
        Safe to call multiple times (idempotent).

        Raises:
            FilesystemError: If cleanup fails
        """
        import shutil

        # Unmount first
        await self.unmount()

        # Remove all files and subdirectories, but keep host_path itself
        try:
            self._logger.info(
                "filesystem_cleaning",
                timestamp=datetime.now(ET).isoformat(),
            )

            for item in self.host_path.iterdir():
                if item.is_dir():
                    await asyncio.get_event_loop().run_in_executor(
                        None, shutil.rmtree, item
                    )
                else:
                    await asyncio.get_event_loop().run_in_executor(None, item.unlink)

            self._logger.info(
                "filesystem_cleaned",
                timestamp=datetime.now(ET).isoformat(),
            )

        except Exception as e:
            self._logger.error(
                "filesystem_cleanup_failed",
                error=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(ET).isoformat(),
            )
            raise FilesystemError(f"Failed to cleanup filesystem: {e}") from e

    async def __aenter__(self) -> "FilesystemShare":
        """Async context manager entry.

        Mounts filesystem on entry.

        Returns:
            Self for use in async with statement
        """
        await self.mount()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Async context manager exit.

        Unmounts filesystem on exit, even if exception occurred.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        await self.unmount()
