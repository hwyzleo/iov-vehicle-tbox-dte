"""Abstract base class for transport implementations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dte.config.transport_profile import TransportProfile

class BaseTransport(ABC):
    """Abstract base class for diagnostic transport implementations.

    Provides a common interface for different transport mechanisms
    (DoIP, CAN/ISO-TP, etc.) used in UDS communication.
    """

    @property
    @abstractmethod
    def profile(self) -> TransportProfile:
        """Return the transport profile configuration."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the transport is currently connected."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the target."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the target."""

    @abstractmethod
    def send_recv(self, data: bytes, timeout: float = 5.0) -> bytes:
        """Send UDS request and receive response.

        Args:
            data: UDS request bytes to send.
            timeout: Maximum time to wait for response in seconds.

        Returns:
            Response bytes from the target.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If no response received within timeout.
        """

    def __enter__(self) -> BaseTransport:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[object],
    ) -> None:
        """Context manager exit."""
        self.disconnect()
