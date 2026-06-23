"""UDS client wrapper using udsoncan library.

Provides a simplified interface over udsoncan's Client for
TBOX diagnostic operations.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Optional, Union

from udsoncan import ClientConfig, DidCodec
from udsoncan.client import Client as UdsClient
from udsoncan.connections import BaseConnection

from dte.uds.security import SecurityAccessAdapter

logger = logging.getLogger(__name__)


class UDSError(Exception):
    """Raised when a UDS operation fails."""


@dataclass
class UDSResponse:
    """Simplified UDS response wrapper.

    Attributes:
        service_id: Response service ID (0x7F for negative).
        positive: Whether this is a positive response.
        data: Response payload bytes (excluding service ID).
        raw: Full raw response bytes.
        nrc: Negative response code (None for positive responses).
    """

    service_id: int
    positive: bool
    data: bytes
    raw: bytes
    nrc: Optional[int] = None


class TransportConnection(BaseConnection):
    """Adapter bridging dte.transport.BaseTransport to udsoncan BaseConnection.

    This allows udsoncan Client to communicate over any transport
    that implements the BaseTransport interface.
    """

    def __init__(self, transport: Any, name: Optional[str] = None) -> None:
        super().__init__(name=name or "TransportConnection")
        self._transport = transport
        self._open = False
        self._pending_request: Optional[bytes] = None
        self._send_lock = threading.Lock()

    def open(self) -> BaseConnection:
        """Open the underlying transport connection."""
        if not self._transport.is_connected:
            self._transport.connect()
        self._open = True
        return self

    def close(self) -> None:
        """Close the underlying transport connection."""
        self._transport.disconnect()
        self._open = False

    def is_open(self) -> bool:
        """Check if the underlying transport is connected."""
        return self._open and self._transport.is_connected

    def specific_send(self, payload: bytes, timeout: Optional[float] = None) -> None:
        """Send data over the transport.

        Args:
            payload: Raw UDS request bytes to send.
            timeout: Optional timeout in seconds.
        """
        self._transport.send_recv(payload, timeout=timeout or 5.0)

    def specific_wait_frame(
        self, timeout: Optional[float] = None, exception: bool = True
    ) -> Optional[bytes]:
        """Wait for a response frame from the transport.

        Args:
            timeout: Maximum time to wait in seconds.
            exception: Whether to raise on timeout.

        Returns:
            Response bytes or None.
        """
        return b""

    def empty_rxqueue(self) -> None:
        """Clear the receive queue (no-op for transport adapter)."""

    def send(
        self, data: Union[bytes, Any, Any], timeout: Optional[float] = None
    ) -> None:
        """Store data to be sent (called by udsoncan before wait_frame).

        Args:
            data: Request data bytes.
            timeout: Optional timeout in seconds.
        """
        self._pending_request: Optional[bytes] = (
            bytes(data) if not isinstance(data, bytes) else data
        )

    def wait_frame(
        self, timeout: Optional[float] = None, exception: bool = True
    ) -> Optional[bytes]:
        """Send the pending request and wait for response.

        Combines send + wait into a single send_recv call.
        Uses a lock to prevent concurrent requests from mixing responses.

        Args:
            timeout: Maximum time to wait in seconds.
            exception: Whether to raise on timeout.

        Returns:
            Response bytes or None.
        """
        if self._pending_request is None:
            return None
        with self._send_lock:
            response = self._transport.send_recv(self._pending_request, timeout=timeout or 5.0)
        self._pending_request = None
        return response


class _FlexibleDidCodec(DidCodec):
    """DidCodec that accepts any remaining payload after DID echo."""

    def decode(self, did_payload: bytes) -> bytes:
        return did_payload

    def encode(self, *did_value: Any) -> bytes:
        return did_value[0] if did_value else b""

    def __len__(self) -> int:
        raise DidCodec.ReadAllRemainingData


def _default_config() -> ClientConfig:
    """Create default ClientConfig with common TBOX DID definitions."""
    config = ClientConfig()
    config["data_identifiers"] = {
        0xF190: _FlexibleDidCodec(),   # VIN - variable length
        0xF191: _FlexibleDidCodec(),   # Binding State - variable length
    }
    return config


class UDSClient:
    """UDS client wrapper providing simplified diagnostic operations.

    Wraps udsoncan's Client to provide a cleaner interface for
    common TBOX diagnostic operations.

    Example:
        ```python
        adapter = FixedKeyAdapter(key=b"\\x12\\x34")
        client = UDSClient(security_adapter=adapter)

        # With a transport connection
        transport = DoIPTransport(config)
        transport.connect()
        conn = TransportConnection(transport)
        client.set_connection(conn)

        # Perform operations
        client.session_control(SessionType.EXTENDED)
        client.security_access(0x01)
        vin = client.read_did(0xF190)
        ```
    """

    def __init__(
        self,
        conn: Optional[Union[BaseConnection, Any]] = None,
        security_adapter: Optional[SecurityAccessAdapter] = None,
        config: Optional[ClientConfig] = None,
    ) -> None:
        """Initialize UDS client.

        Args:
            conn: udsoncan BaseConnection or BaseTransport instance.
            security_adapter: Optional adapter for seed-to-key computation.
            config: Optional udsoncan ClientConfig overrides.
        """
        self._conn = conn
        self._security_adapter = security_adapter
        self._config: ClientConfig = config if config is not None else _default_config()
        self._client: Optional[UdsClient] = None

    def set_connection(self, conn: Union[BaseConnection, Any]) -> None:
        """Set or replace the connection.

        Args:
            conn: udsoncan BaseConnection or BaseTransport instance.
        """
        self._conn = conn

    def _get_client(self) -> UdsClient:
        """Get or create the underlying udsoncan Client.

        Returns:
            Configured udsoncan Client instance.

        Raises:
            UDSError: If no connection is set.
        """
        if self._conn is None:
            raise UDSError("Not connected")

        if self._client is None:
            connection = self._conn
            if not isinstance(connection, BaseConnection):
                connection = TransportConnection(connection)
            self._client = UdsClient(connection, config=self._config)
            self._client.open()
        return self._client

    def _wrap_response(
        self,
        response: Any,
        expected_service_id: int,
    ) -> UDSResponse:
        """Convert udsoncan response to UDSResponse.

        Args:
            response: udsoncan InterpretedResponse.
            expected_service_id: Expected positive response service ID.

        Returns:
            UDSResponse instance.
        """
        if response is None:
            raise UDSError("No response received")

        raw = response.original_payload if hasattr(response, "original_payload") else b""
        service_data = getattr(response, "service_data", None)

        if response.valid:
            return UDSResponse(
                service_id=expected_service_id,
                positive=True,
                data=raw[1:] if len(raw) > 1 else b"",
                raw=raw,
            )
        else:
            code = getattr(service_data, "nrc", None) if service_data else None
            return UDSResponse(
                service_id=0x7F,
                positive=False,
                data=raw,
                raw=raw,
                nrc=code,
            )

    def session_control(self, session_type: int) -> UDSResponse:
        """Switch diagnostic session (0x10).

        Args:
            session_type: Session type (e.g., 0x01=Default, 0x02=Programming,
                         0x03=Extended).

        Returns:
            UDSResponse with session control result.
        """
        client = self._get_client()
        response = client.change_session(session_type)
        return self._wrap_response(response, 0x50)

    def tester_present(self) -> UDSResponse:
        """Send TesterPresent (0x3E) to keep session alive.

        Returns:
            UDSResponse with tester present result.
        """
        client = self._get_client()
        response = client.tester_present()
        return self._wrap_response(response, 0x7E)

    def read_did(self, did: int) -> UDSResponse:
        """Read data by identifier (0x22).

        Args:
            did: Data identifier to read (e.g., 0xF190 for VIN).

        Returns:
            UDSResponse with read data.
        """
        client = self._get_client()
        response = client.read_data_by_identifier(did)
        return self._wrap_response(response, 0x62)

    def write_did(self, did: int, data: Union[bytes, Any]) -> UDSResponse:
        """Write data by identifier (0x2E).

        Args:
            did: Data identifier to write.
            data: Data to write.

        Returns:
            UDSResponse with write result.
        """
        client = self._get_client()
        response = client.write_data_by_identifier(did, data)
        return self._wrap_response(response, 0x6E)

    def security_access(
        self,
        level: int,
        seed_to_key: bytes = b"",
    ) -> UDSResponse:
        """Perform security access (0x27).

        Sends a seed request, computes the key using the configured
        security adapter, and sends the key.

        Args:
            level: Security access level (must be odd for seed request).
            seed_to_key: Optional extra data for seed request.

        Returns:
            UDSResponse with security access result.

        Raises:
            UDSError: If no security adapter configured.
        """
        if self._security_adapter is None:
            raise UDSError("No security adapter configured")

        client = self._get_client()

        seed_response = client.request_seed(level, data=seed_to_key)
        if seed_response is None or not seed_response.valid:
            return self._wrap_response(seed_response, 0x67)

        seed = getattr(seed_response.service_data, "seed", b"")
        key_level = level + 1
        key = self._security_adapter.compute_key(seed, key_level)

        # udsoncan's send_key rejects level > 0x7E, but SecurityAccess protocol
        # requires bit 7=1 for send_key sub-function. Send raw UDS request instead.
        send_key_sub = key_level | 0x80
        raw_request = bytes([0x27, send_key_sub]) + key
        self._conn.send(raw_request)
        raw_response = self._conn.wait_frame(timeout=5.0)

        if raw_response is None:
            raise UDSError("No response for send_key")

        key_response = UDSResponse(
            service_id=raw_response[0] if raw_response else 0,
            positive=raw_response[0] != 0x7F if raw_response else False,
            data=raw_response[1:] if len(raw_response) > 1 else b"",
            raw=raw_response,
            nrc=raw_response[2] if len(raw_response) > 2 and raw_response[0] == 0x7F else None,
        )
        return key_response

    def routine_control(
        self,
        routine_id: int,
        control_type: int,
        data: Optional[bytes] = None,
    ) -> UDSResponse:
        """Execute routine control (0x31).

        Args:
            routine_id: Routine identifier.
            control_type: Routine control sub-function
                         (0x01=Start, 0x02=Stop, 0x03=RequestResults).
            data: Optional routine data.

        Returns:
            UDSResponse with routine result.
        """
        client = self._get_client()
        if control_type == 0x01:
            response = client.start_routine(routine_id, data=data)
        elif control_type == 0x02:
            response = client.stop_routine(routine_id, data=data)
        elif control_type == 0x03:
            response = client.get_routine_result(routine_id, data=data)
        else:
            raise UDSError(f"Unsupported routine control type: {control_type}")
        return self._wrap_response(response, 0x71)

    def read_dtc(self, status_mask: int) -> UDSResponse:
        """Read DTC information by status mask (0x19 sub-function 0x02).

        Args:
            status_mask: DTC status mask.

        Returns:
            UDSResponse with DTC information.
        """
        client = self._get_client()
        response = client.get_dtc_by_status_mask(status_mask)
        return self._wrap_response(response, 0x59)

    def clear_dtc(self, group: int = 0xFFFFFF) -> UDSResponse:
        """Clear DTC information (0x14).

        Args:
            group: DTC group (0xFFFFFF = all DTCs).

        Returns:
            UDSResponse with clear result.
        """
        client = self._get_client()
        response = client.clear_dtc(group)
        return self._wrap_response(response, 0x54)

    def io_control(
        self,
        did: int,
        control_type: int = 0x03,
        data: Optional[Any] = None,
    ) -> UDSResponse:
        """Input/Output control by identifier (0x2F).

        Args:
            did: Data identifier for I/O control.
            control_type: I/O control type (e.g., 0x03=shortTermAdjustment).
            data: Optional control data.

        Returns:
            UDSResponse with I/O control result.
        """
        client = self._get_client()
        response = client.io_control(did, control_param=control_type, values=data)
        return self._wrap_response(response, 0x6F)

    def __enter__(self) -> UDSClient:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[object],
    ) -> None:
        """Context manager exit - close connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
        elif self._conn is not None and hasattr(self._conn, "close"):
            self._conn.close()
