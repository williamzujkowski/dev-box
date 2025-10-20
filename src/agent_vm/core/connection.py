"""Libvirt connection management.

This module provides a thread-safe wrapper around libvirt connections with
proper error handling, context manager support, and structured logging.
"""

import libvirt
import structlog

logger = structlog.get_logger()


class ConnectionError(Exception):
    """Custom exception for connection-related errors."""

    pass


class LibvirtConnection:
    """Thread-safe libvirt connection wrapper.

    Provides a high-level interface for managing libvirt connections with
    proper resource cleanup, error handling, and logging.

    Example:
        >>> with LibvirtConnection() as conn:
        ...     domains = conn.connection.listAllDomains()
        ...     for domain in domains:
        ...         print(domain.name())
    """

    def __init__(self, uri: str = "qemu:///system") -> None:
        """Initialize connection manager.

        Args:
            uri: libvirt URI to connect to. Defaults to qemu:///system.
        """
        self._uri = uri
        self._conn: libvirt.virConnect | None = None

    def open(self) -> None:
        """Open connection to libvirt.

        Raises:
            ConnectionError: If connection fails or libvirt.open returns None.
        """
        # Skip if already connected
        if self.is_connected():
            logger.debug("libvirt_connection_already_open", uri=self._uri)
            return

        try:
            logger.debug("libvirt_connection_opening", uri=self._uri)
            self._conn = libvirt.open(self._uri)

            if self._conn is None:
                raise ConnectionError(f"libvirt.open returned None for URI: {self._uri}")

            logger.info("libvirt_connection_opened", uri=self._uri)

        except libvirt.libvirtError as e:
            logger.error("libvirt_connection_failed", uri=self._uri, error=str(e))
            raise ConnectionError(f"Failed to connect to {self._uri}: {e}") from e
        except Exception as e:
            logger.error("libvirt_connection_failed", uri=self._uri, error=str(e))
            raise ConnectionError(f"Failed to connect to {self._uri}: {e}") from e

    def close(self) -> None:
        """Close connection to libvirt.

        This method is idempotent - calling it multiple times is safe.
        Handles errors gracefully to ensure cleanup happens.
        """
        if self._conn is None:
            return

        try:
            logger.debug("libvirt_connection_closing", uri=self._uri)
            self._conn.close()
            logger.info("libvirt_connection_closed", uri=self._uri)
        except Exception as e:
            logger.error(
                "libvirt_connection_close_failed",
                uri=self._uri,
                error=str(e),
            )
            # Don't raise - we still want to clean up internal state
        finally:
            self._conn = None

    def is_connected(self) -> bool:
        """Check if connection is active and healthy.

        Returns:
            True if connected and alive, False otherwise.
        """
        if self._conn is None:
            return False

        try:
            # isAlive() returns 1 if alive, 0 if dead
            alive_status = self._conn.isAlive()
            return bool(alive_status == 1)
        except Exception:
            return False

    @property
    def connection(self) -> libvirt.virConnect:
        """Get underlying libvirt connection object.

        Returns:
            The active libvirt connection.

        Raises:
            ConnectionError: If not connected.
        """
        if self._conn is None:
            raise ConnectionError("Not connected to libvirt")
        return self._conn

    def __enter__(self) -> "LibvirtConnection":
        """Enter context manager - opens connection.

        Returns:
            Self for use in with statement.
        """
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit context manager - closes connection.

        Args:
            exc_type: Exception type if exception occurred.
            exc_val: Exception value if exception occurred.
            exc_tb: Exception traceback if exception occurred.
        """
        self.close()
