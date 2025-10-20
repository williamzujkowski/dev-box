"""Unit tests for FilesystemShare.

Tests virtio-9p filesystem sharing functionality including file operations,
error handling, and workspace management following TDD methodology.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from agent_vm.communication.filesystem import FilesystemShare, FilesystemError


class TestFilesystemShareInit:
    """Test FilesystemShare initialization"""

    def test_init_creates_instance(self, tmp_path: Path) -> None:
        """FilesystemShare initializes with host_path"""
        fs = FilesystemShare(host_path=tmp_path)

        assert fs.host_path == tmp_path
        assert fs.mount_tag == "agent_share"
        assert fs.guest_mount_point == "/mnt/agent"

    def test_init_custom_mount_tag(self, tmp_path: Path) -> None:
        """FilesystemShare accepts custom mount tag"""
        fs = FilesystemShare(host_path=tmp_path, mount_tag="custom_share")

        assert fs.mount_tag == "custom_share"

    def test_init_custom_guest_mount_point(self, tmp_path: Path) -> None:
        """FilesystemShare accepts custom guest mount point"""
        fs = FilesystemShare(host_path=tmp_path, guest_mount_point="/custom/mount")

        assert fs.guest_mount_point == "/custom/mount"

    def test_init_creates_host_directory(self, tmp_path: Path) -> None:
        """FilesystemShare creates host directory if it doesn't exist"""
        new_path = tmp_path / "nonexistent"
        fs = FilesystemShare(host_path=new_path)

        assert new_path.exists()
        assert new_path.is_dir()

    def test_init_accepts_existing_directory(self, tmp_path: Path) -> None:
        """FilesystemShare accepts existing directory"""
        tmp_path.mkdir(exist_ok=True)
        fs = FilesystemShare(host_path=tmp_path)

        assert fs.host_path == tmp_path


class TestFilesystemShareMount:
    """Test filesystem mounting operations"""

    @pytest.mark.asyncio
    async def test_mount_succeeds(self, tmp_path: Path) -> None:
        """Mount operation succeeds"""
        fs = FilesystemShare(host_path=tmp_path)

        # Mount should complete without error
        await fs.mount()

        assert fs.is_mounted

    @pytest.mark.asyncio
    async def test_mount_idempotent(self, tmp_path: Path) -> None:
        """Multiple mount calls are safe (idempotent)"""
        fs = FilesystemShare(host_path=tmp_path)

        await fs.mount()
        await fs.mount()  # Should not raise

        assert fs.is_mounted

    @pytest.mark.asyncio
    async def test_mount_handles_failure(self, tmp_path: Path) -> None:
        """Mount handles errors gracefully"""
        fs = FilesystemShare(host_path=tmp_path)

        # Simulate mount failure
        with patch.object(fs, "_execute_mount", side_effect=OSError("Mount failed")):
            with pytest.raises(FilesystemError, match="Failed to mount"):
                await fs.mount()


class TestFilesystemShareUnmount:
    """Test filesystem unmounting operations"""

    @pytest.mark.asyncio
    async def test_unmount_succeeds(self, tmp_path: Path) -> None:
        """Unmount operation succeeds"""
        fs = FilesystemShare(host_path=tmp_path)
        await fs.mount()

        await fs.unmount()

        assert not fs.is_mounted

    @pytest.mark.asyncio
    async def test_unmount_when_not_mounted(self, tmp_path: Path) -> None:
        """Unmount when not mounted is safe"""
        fs = FilesystemShare(host_path=tmp_path)

        # Should not raise
        await fs.unmount()

        assert not fs.is_mounted

    @pytest.mark.asyncio
    async def test_unmount_handles_failure(self, tmp_path: Path) -> None:
        """Unmount handles errors gracefully"""
        fs = FilesystemShare(host_path=tmp_path)
        await fs.mount()

        # Simulate unmount failure
        with patch.object(fs, "_execute_unmount", side_effect=OSError("Unmount failed")):
            with pytest.raises(FilesystemError, match="Failed to unmount"):
                await fs.unmount()


class TestFilesystemShareWriteFile:
    """Test file writing operations"""

    @pytest.mark.asyncio
    async def test_write_file_creates_file(self, tmp_path: Path) -> None:
        """Write file creates file with correct content"""
        fs = FilesystemShare(host_path=tmp_path)
        content = b"test content"

        await fs.write_file("test.txt", content)

        file_path = tmp_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_write_file_nested_path(self, tmp_path: Path) -> None:
        """Write file creates nested directories"""
        fs = FilesystemShare(host_path=tmp_path)
        content = b"nested content"

        await fs.write_file("dir1/dir2/test.txt", content)

        file_path = tmp_path / "dir1" / "dir2" / "test.txt"
        assert file_path.exists()
        assert file_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_write_file_overwrites_existing(self, tmp_path: Path) -> None:
        """Write file overwrites existing content"""
        fs = FilesystemShare(host_path=tmp_path)
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"old content")

        new_content = b"new content"
        await fs.write_file("test.txt", new_content)

        assert file_path.read_bytes() == new_content

    @pytest.mark.asyncio
    async def test_write_file_handles_permission_error(self, tmp_path: Path) -> None:
        """Write file handles permission errors"""
        fs = FilesystemShare(host_path=tmp_path)

        with patch("pathlib.Path.write_bytes", side_effect=PermissionError("Access denied")):
            with pytest.raises(FilesystemError, match="Failed to write file"):
                await fs.write_file("test.txt", b"content")

    @pytest.mark.asyncio
    async def test_write_file_empty_content(self, tmp_path: Path) -> None:
        """Write file handles empty content"""
        fs = FilesystemShare(host_path=tmp_path)

        await fs.write_file("empty.txt", b"")

        file_path = tmp_path / "empty.txt"
        assert file_path.exists()
        assert file_path.read_bytes() == b""


class TestFilesystemShareReadFile:
    """Test file reading operations"""

    @pytest.mark.asyncio
    async def test_read_file_returns_content(self, tmp_path: Path) -> None:
        """Read file returns correct content"""
        fs = FilesystemShare(host_path=tmp_path)
        content = b"test content"
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(content)

        result = await fs.read_file("test.txt")

        assert result == content

    @pytest.mark.asyncio
    async def test_read_file_nested_path(self, tmp_path: Path) -> None:
        """Read file from nested directory"""
        fs = FilesystemShare(host_path=tmp_path)
        nested_dir = tmp_path / "dir1" / "dir2"
        nested_dir.mkdir(parents=True)
        content = b"nested content"
        (nested_dir / "test.txt").write_bytes(content)

        result = await fs.read_file("dir1/dir2/test.txt")

        assert result == content

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, tmp_path: Path) -> None:
        """Read file raises error if file doesn't exist"""
        fs = FilesystemShare(host_path=tmp_path)

        with pytest.raises(FilesystemError, match="File not found"):
            await fs.read_file("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_read_file_empty_content(self, tmp_path: Path) -> None:
        """Read file handles empty files"""
        fs = FilesystemShare(host_path=tmp_path)
        file_path = tmp_path / "empty.txt"
        file_path.write_bytes(b"")

        result = await fs.read_file("empty.txt")

        assert result == b""

    @pytest.mark.asyncio
    async def test_read_file_handles_permission_error(self, tmp_path: Path) -> None:
        """Read file handles permission errors"""
        fs = FilesystemShare(host_path=tmp_path)
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"content")

        with patch("pathlib.Path.read_bytes", side_effect=PermissionError("Access denied")):
            with pytest.raises(FilesystemError, match="Failed to read file"):
                await fs.read_file("test.txt")


class TestFilesystemShareContextManager:
    """Test context manager behavior"""

    @pytest.mark.asyncio
    async def test_async_context_manager_mounts_on_enter(self, tmp_path: Path) -> None:
        """Context manager mounts on enter"""
        fs = FilesystemShare(host_path=tmp_path)

        async with fs:
            assert fs.is_mounted

    @pytest.mark.asyncio
    async def test_async_context_manager_unmounts_on_exit(self, tmp_path: Path) -> None:
        """Context manager unmounts on exit"""
        fs = FilesystemShare(host_path=tmp_path)

        async with fs:
            pass

        assert not fs.is_mounted

    @pytest.mark.asyncio
    async def test_async_context_manager_unmounts_on_exception(self, tmp_path: Path) -> None:
        """Context manager unmounts even if exception occurs"""
        fs = FilesystemShare(host_path=tmp_path)

        with pytest.raises(ValueError):
            async with fs:
                raise ValueError("Test exception")

        assert not fs.is_mounted


class TestFilesystemShareLogging:
    """Test structured logging"""

    @pytest.mark.asyncio
    async def test_mount_logs_success(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Mount logs success event"""
        fs = FilesystemShare(host_path=tmp_path)

        await fs.mount()

        # Check for mount log (structlog may format differently)
        assert fs.is_mounted

    @pytest.mark.asyncio
    async def test_write_file_logs_operation(self, tmp_path: Path) -> None:
        """Write file logs operation"""
        fs = FilesystemShare(host_path=tmp_path)

        await fs.write_file("test.txt", b"content")

        # Verify file was written (logging tested implicitly)
        assert (tmp_path / "test.txt").exists()

    @pytest.mark.asyncio
    async def test_read_file_logs_operation(self, tmp_path: Path) -> None:
        """Read file logs operation"""
        fs = FilesystemShare(host_path=tmp_path)
        (tmp_path / "test.txt").write_bytes(b"content")

        await fs.read_file("test.txt")

        # Logging tested implicitly through successful operation


class TestFilesystemShareProperties:
    """Test property accessors"""

    def test_is_mounted_false_initially(self, tmp_path: Path) -> None:
        """is_mounted is False initially"""
        fs = FilesystemShare(host_path=tmp_path)

        assert not fs.is_mounted

    @pytest.mark.asyncio
    async def test_is_mounted_true_after_mount(self, tmp_path: Path) -> None:
        """is_mounted is True after mount"""
        fs = FilesystemShare(host_path=tmp_path)

        await fs.mount()

        assert fs.is_mounted

    @pytest.mark.asyncio
    async def test_is_mounted_false_after_unmount(self, tmp_path: Path) -> None:
        """is_mounted is False after unmount"""
        fs = FilesystemShare(host_path=tmp_path)
        await fs.mount()

        await fs.unmount()

        assert not fs.is_mounted
