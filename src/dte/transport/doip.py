"""DoIP (Diagnostics over IP) transport implementation."""
from __future__ import annotations

from typing import Optional

from doipclient import DoIPClient

from dte.config.transport_profile import DoIPConfig, TransportProfile

from .base import BaseTransport
from .exceptions import ConnectionError


class DoIPTransport(BaseTransport):
    """DoIP transport for diagnostic communication over Ethernet.

    Uses the doipclient library to communicate with DoIP-capable
    ECU gateways.
    """

    def __init__(self, config: DoIPConfig, profile: Optional[TransportProfile] = None) -> None:
        """Initialize DoIP transport.

        Args:
            config: DoIP configuration parameters.
            profile: Optional transport profile for metadata.
        """
        self.config = config
        self._profile = profile
        self._client: Optional[DoIPClient] = None

    @property
    def profile(self) -> TransportProfile:
        """Return the transport profile configuration."""
        if self._profile is None:
            raise AttributeError("No profile configured for this transport")
        return self._profile

    @property
    def is_connected(self) -> bool:
        """Return whether the transport is currently connected."""
        return self._client is not None

    def connect(self) -> None:
        """Establish DoIP connection to the target."""
        self._client = DoIPClient(
            self.config.target_ip,
            self.config.target_addr,
            tcp_port=self.config.tcp_port,
            activation_type=self.config.activation_type,
            client_logical_address=self.config.source_addr,
        )

    def disconnect(self) -> None:
        """Close DoIP connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def send_recv(self, data: bytes, timeout: float = 5.0) -> bytes:
        """Send UDS request and receive response via DoIP.

        Args:
            data: UDS request bytes to send.
            timeout: Maximum time to wait for response in seconds.

        Returns:
            Response bytes from the target.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If no response received within timeout.
        """
        if self._client is None:
            raise ConnectionError("Not connected")

        self._client.send_diagnostic(data, timeout=timeout)
        response = self._client.receive_diagnostic(timeout=timeout)
        return bytes(response)
