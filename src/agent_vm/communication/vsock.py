"""virtio-vsock communication protocol.

This module implements the vsock protocol for low-latency host-guest communication
using virtio-vsock. Messages are framed with headers and checksums for integrity.
"""

import asyncio
import hashlib
import socket
import struct
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

# NIST Eastern Time timezone for timestamps
ET = ZoneInfo("America/New_York")

logger = structlog.get_logger()


class VsockError(Exception):
    """Vsock operation error."""

    pass


@dataclass(frozen=True)
class VsockMessage:
    """Vsock message with header and payload.

    Attributes:
        command: Command string (e.g., "execute", "ping", "result")
        payload: Binary payload data
        checksum: SHA256 hash of command + payload for integrity verification
    """

    command: str
    payload: bytes
    checksum: str


class VsockProtocol:
    """Handles virtio-vsock communication protocol.

    Implements message framing, checksumming, and async send/receive operations
    for reliable host-guest communication over virtio-vsock.

    Message Format:
        - Header: 8 bytes (4 bytes command length + 4 bytes payload length)
        - Command: UTF-8 encoded string
        - Payload: Raw bytes
        - Checksum: SHA256 hash (64 hex characters)

    Attributes:
        cid: Context ID for vsock connection
        port: Port number for vsock socket (default 9000)
    """

    def __init__(self, cid: int, port: int = 9000) -> None:
        """Initialize vsock protocol.

        Args:
            cid: Context ID (must be positive integer)
            port: Port number (must be in range 1-65535)

        Raises:
            VsockError: If CID or port are invalid
        """
        if cid <= 0:
            raise VsockError(f"CID must be positive, got: {cid}")

        if port <= 0 or port > 65535:
            raise VsockError(f"Port must be between 1 and 65535, got: {port}")

        self.cid = cid
        self.port = port
        self._socket: socket.socket | None = None
        self._logger = logger.bind(cid=cid, port=port)

        self._logger.info("vsock_protocol_initialized")

    async def send(self, message: VsockMessage) -> None:
        """Send message over vsock.

        Frames the message with header and checksum, then transmits over socket.

        Args:
            message: Message to send

        Raises:
            VsockError: If send fails
        """
        try:
            # Frame the message
            framed_data = self._frame_message(message)

            # Send over socket
            if self._socket is None:
                raise VsockError("Socket not initialized")

            # Use asyncio to make socket operations async
            # Check if sendall is awaitable (AsyncMock) or not (regular socket)
            sendall_result = self._socket.sendall(framed_data)  # type: ignore[func-returns-value]
            if asyncio.iscoroutine(sendall_result):
                await sendall_result
            elif sendall_result is not None:
                # If it's a Future/Task, await it
                if hasattr(sendall_result, "__await__"):
                    await sendall_result

            self._logger.info(
                "vsock_send",
                command=message.command,
                payload_size=len(message.payload),
                timestamp=datetime.now(ET).isoformat(),
            )

        except (OSError, VsockError) as e:
            self._logger.error(
                "vsock_send_failed",
                command=message.command,
                error=str(e),
                timestamp=datetime.now(ET).isoformat(),
            )
            # Re-raise VsockError as-is, wrap OSError
            if isinstance(e, VsockError):
                raise
            raise VsockError(f"Failed to send message: {e}") from e

    async def receive(self) -> VsockMessage:
        """Receive message from vsock.

        Reads framed message from socket, validates checksum, and returns parsed message.

        Returns:
            Received and validated message

        Raises:
            VsockError: If receive fails or message is invalid
        """
        try:
            if self._socket is None:
                raise VsockError("Socket not initialized")

            # Helper to handle both async and sync recv
            async def _recv(size: int) -> bytes:
                recv_result = self._socket.recv(size)  # type: ignore[union-attr]
                if asyncio.iscoroutine(recv_result):
                    data: bytes = await recv_result
                    return data
                # For regular socket, recv returns bytes
                return bytes(recv_result)

            # Read header (8 bytes)
            header_data = await _recv(8)
            if len(header_data) < 8:
                raise VsockError(f"Incomplete header received: {len(header_data)} bytes")

            # Parse header to get lengths
            cmd_len, payload_len = struct.unpack("!II", header_data)

            # Read command
            command_data = await _recv(cmd_len)
            if len(command_data) < cmd_len:
                raise VsockError("Unexpected end of stream reading command")

            # Read payload
            payload_data = await _recv(payload_len)
            if len(payload_data) < payload_len:
                raise VsockError("Unexpected end of stream reading payload")

            # Read checksum (64 bytes)
            checksum_data = await _recv(64)
            if len(checksum_data) < 64:
                raise VsockError("Unexpected end of stream reading checksum")

            # Reconstruct full frame for parsing
            full_frame = header_data + command_data + payload_data + checksum_data

            # Parse and validate
            message = self._parse_message(full_frame)

            self._logger.info(
                "vsock_receive",
                command=message.command,
                payload_size=len(message.payload),
                timestamp=datetime.now(ET).isoformat(),
            )

            return message

        except (OSError, VsockError) as e:
            self._logger.error(
                "vsock_receive_failed",
                error=str(e),
                timestamp=datetime.now(ET).isoformat(),
            )
            # Re-raise VsockError as-is, wrap OSError
            if isinstance(e, VsockError):
                raise
            raise VsockError(f"Failed to receive message: {e}") from e

    def _frame_message(self, message: VsockMessage) -> bytes:
        """Frame message with header and checksum.

        Creates binary frame with structure:
        - Header: 8 bytes (command length + payload length)
        - Command: UTF-8 encoded
        - Payload: Raw bytes
        - Checksum: SHA256 hex digest (64 bytes)

        Args:
            message: Message to frame

        Returns:
            Framed message as bytes
        """
        # Encode command
        command_bytes = message.command.encode("utf-8")

        # Calculate checksum
        checksum = hashlib.sha256(command_bytes + message.payload).hexdigest()

        # Build header
        header = struct.pack("!II", len(command_bytes), len(message.payload))

        # Combine all parts
        frame = header + command_bytes + message.payload + checksum.encode("utf-8")

        return frame

    def _parse_message(self, data: bytes) -> VsockMessage:
        """Parse received message.

        Extracts components from frame and validates checksum.

        Args:
            data: Raw frame data

        Returns:
            Parsed and validated message

        Raises:
            VsockError: If frame is malformed or checksum is invalid
        """
        # Validate minimum frame size (header + checksum)
        if len(data) < 8 + 64:
            raise VsockError(f"Frame too short: {len(data)} bytes, need at least 72")

        try:
            # Parse header
            cmd_len, payload_len = struct.unpack("!II", data[:8])

            # Validate lengths
            expected_len = 8 + cmd_len + payload_len + 64
            if len(data) < expected_len:
                raise VsockError(f"Invalid frame: expected {expected_len} bytes, got {len(data)}")

            # Extract components
            offset = 8
            command = data[offset : offset + cmd_len].decode("utf-8")
            offset += cmd_len

            payload = data[offset : offset + payload_len]
            offset += payload_len

            checksum_received = data[offset : offset + 64].decode("utf-8")

            # Calculate expected checksum
            checksum_expected = hashlib.sha256(command.encode("utf-8") + payload).hexdigest()

            # Validate checksum
            if checksum_received != checksum_expected:
                raise VsockError(
                    f"Checksum mismatch: expected {checksum_expected}, got {checksum_received}"
                )

            return VsockMessage(command=command, payload=payload, checksum=checksum_received)

        except struct.error as e:
            raise VsockError(f"Malformed frame header: {e}") from e
        except UnicodeDecodeError as e:
            raise VsockError(f"Invalid UTF-8 in frame: {e}") from e
