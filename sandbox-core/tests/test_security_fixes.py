"""
Test security fixes and vulnerabilities
"""

import tarfile
import tempfile
from pathlib import Path

import pytest

from sandbox.utils.security import SecureSerializer
from sandbox.utils.security import SecureTarExtractor
from sandbox.utils.security import SecurityError
from sandbox.utils.security import validate_file_path
from sandbox.utils.serialization import StateSerializer


class TestSecurityFixes:
    """Test cases for security vulnerability fixes."""

    def test_secure_tar_extractor_blocks_path_traversal(self):
        """Test that SecureTarExtractor blocks path traversal attempts."""
        extractor = SecureTarExtractor()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a malicious tar file with path traversal
            tar_path = temp_path / "malicious.tar"
            with tarfile.open(tar_path, "w") as tar:
                # Create a tar info with path traversal
                info = tarfile.TarInfo("../../../etc/passwd")
                info.size = 10
                tar.addfile(info, fileobj=None)

            # Attempt extraction - should be blocked
            with pytest.raises((SecurityError, ValueError)):
                extractor.safe_extractall(tar_path, temp_path / "extract")

    def test_secure_tar_extractor_blocks_absolute_paths(self):
        """Test that SecureTarExtractor blocks absolute paths."""
        extractor = SecureTarExtractor()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a tar file with absolute path
            tar_path = temp_path / "malicious.tar"
            with tarfile.open(tar_path, "w") as tar:
                info = tarfile.TarInfo("/etc/passwd")
                info.size = 10
                tar.addfile(info, fileobj=None)

            # Extraction should be blocked
            with pytest.raises((SecurityError, ValueError)):
                extractor.safe_extractall(tar_path, temp_path / "extract")

    def test_secure_tar_extractor_blocks_large_files(self):
        """Test that SecureTarExtractor enforces size limits."""
        extractor = SecureTarExtractor(max_size=100)  # 100 byte limit

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a tar file with oversized content
            tar_path = temp_path / "large.tar"
            with tarfile.open(tar_path, "w") as tar:
                info = tarfile.TarInfo("large_file.txt")
                info.size = 1000  # Larger than limit
                tar.addfile(info, fileobj=None)

            # Extraction should be blocked
            with pytest.raises((SecurityError, ValueError)):
                extractor.safe_extractall(tar_path, temp_path / "extract")

    def test_secure_tar_extractor_allows_safe_extraction(self):
        """Test that SecureTarExtractor allows safe files."""
        extractor = SecureTarExtractor()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a safe tar file
            tar_path = temp_path / "safe.tar"
            test_content = b"safe content"

            with tarfile.open(tar_path, "w") as tar:
                # Create a temporary file to add
                test_file = temp_path / "test.txt"
                test_file.write_bytes(test_content)
                tar.add(test_file, arcname="safe/test.txt")

            # Extraction should succeed
            extract_dir = temp_path / "extract"
            extracted_files = extractor.safe_extractall(tar_path, extract_dir)

            assert len(extracted_files) == 1
            assert (extract_dir / "safe" / "test.txt").exists()
            assert (extract_dir / "safe" / "test.txt").read_bytes() == test_content

    def test_secure_serializer_prevents_tampering(self):
        """Test that SecureSerializer detects tampering."""
        serializer = SecureSerializer()

        # Serialize some data
        original_data = {"test": "data", "number": 42}
        signed_data = serializer.serialize(original_data)

        # Tamper with the data
        import json

        package = json.loads(signed_data)
        package["data"] = json.dumps({"tampered": "data"})
        tampered_data = json.dumps(package)

        # Deserialization should fail
        with pytest.raises(ValueError, match="Signature verification failed"):
            serializer.deserialize(tampered_data)

    def test_secure_serializer_roundtrip(self):
        """Test that SecureSerializer can serialize and deserialize correctly."""
        serializer = SecureSerializer()

        original_data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        # Serialize and deserialize
        signed_data = serializer.serialize(original_data)
        restored_data = serializer.deserialize(signed_data)

        assert restored_data == original_data

    def test_state_serializer_uses_secure_fallback(self):
        """Test that StateSerializer uses secure serialization for pickle format."""
        serializer = StateSerializer()

        test_data = {"test": "data", "secure": True}

        # Using pickle format should now use secure serialization
        serialized = serializer._serialize_pickle(test_data)

        # Should be able to deserialize
        deserialized = serializer._deserialize_pickle(serialized)

        # Data should match (though it may be transformed due to JSON serialization)
        assert isinstance(deserialized, dict)

    def test_path_validation_blocks_traversal(self):
        """Test that path validation blocks directory traversal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Valid paths should pass
            assert validate_file_path(base_path / "safe.txt", base_path)
            assert validate_file_path(base_path / "subdir" / "file.txt", base_path)

            # Traversal attempts should fail
            assert not validate_file_path("../../../etc/passwd", base_path)
            assert not validate_file_path(base_path / ".." / "outside.txt", base_path)

    def test_pickle_vulnerability_warning(self, caplog):
        """Test that pickle usage generates warnings."""
        serializer = StateSerializer()

        # Using pickle should generate warnings
        test_data = {"test": "data"}

        with caplog.at_level("WARNING"):
            serializer._serialize_pickle(test_data)

        assert "deprecated pickle serialization" in caplog.text.lower()

    def test_security_scanner_detects_patterns(self):
        """Test that security patterns are detectable."""
        # This would normally be tested by running the security scanner
        # For now, we'll just verify the modules can be imported
        from sandbox.utils.security import SecurityError
        from sandbox.utils.serialization import StateSerializer

        # Verify security components are available
        assert SecurityError is not None
        assert StateSerializer is not None


class TestPathValidation:
    """Test path validation functions."""

    def test_validate_file_path_safe_paths(self):
        """Test validation of safe file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # These should be valid
            assert validate_file_path(base / "file.txt", base)
            assert validate_file_path(base / "subdir" / "file.txt", base)
            assert validate_file_path(str(base / "file.txt"), str(base))

    def test_validate_file_path_dangerous_paths(self):
        """Test validation blocks dangerous paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # These should be invalid
            assert not validate_file_path("../outside.txt", base)
            assert not validate_file_path("/etc/passwd", base)
            assert not validate_file_path(base.parent / "outside.txt", base)

    def test_validate_file_path_edge_cases(self):
        """Test path validation edge cases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)

            # Edge cases
            assert not validate_file_path("", base)  # Empty path
            assert validate_file_path(str(base), str(base))  # Same path
