"""CAN/ISO-TP transport implementation."""
from __future__ import annotations

from typing import Optional

import can
import isotp

from dte.config.transport_profile import CANAddressing, CANConfig, TransportProfile

from .base import BaseTransport
from .exceptions import ConnectionError, TimeoutError


class CANTransport(BaseTransport):
    """CAN/ISO-TP transport for diagnostic communication.

    Uses python-can for CAN bus access and can-isotp for
    ISO-TP (ISO 15765-2) segmentation.
    """

    def __init__(self, config: CANConfig, profile: Optional[TransportProfile] = None) -> None:
        """Initialize CAN transport.

        Args:
            config: CAN configuration parameters.
            profile: Optional transport profile for metadata.
        """
        self.config = config
        self._profile = profile
        self._bus: Optional[can.BusABC] = None
        self._notifier: Optional[can.Notifier] = None
        self._isotp_layer: Optional[isotp.NotifierBasedCanStack] = None

    @property
    def profile(self) -> TransportProfile:
        """Return the transport profile configuration."""
        if self._profile is None:
            raise AttributeError("No profile configured for this transport")
        return self._profile

    @property
    def is_connected(self) -> bool:
        """Return whether the transport is currently connected."""
        return self._isotp_layer is not None

    def connect(self) -> None:
        """Establish CAN connection and start ISO-TP layer."""
        self._bus = can.Bus(
            interface=self.config.interface,
            channel=self.config.channel,
            bitrate=self.config.bitrate,
        )

        self._notifier = can.Notifier(self._bus, [])

        isotp_params: dict = {
            "txid": self.config.req_id,
            "rxid": self.config.resp_id,
            "block_size": self.config.block_size,
            "st_min": self.config.st_min,
        }

        if self.config.addressing == CANAddressing.EXTENDED:
            isotp_params["txid"] = self.config.req_id
            isotp_params["rxid"] = self.config.resp_id
            isotp_params["addressing_mode"] = isotp.AddressingMode.Extended_11bits
        elif self.config.addressing == CANAddressing.MIXED:
            isotp_params["txid"] = self.config.req_id
            isotp_params["rxid"] = self.config.resp_id
            isotp_params["addressing_mode"] = isotp.AddressingMode.Mixed_29bits

        self._isotp_layer = isotp.NotifierBasedCanStack(
            bus=self._bus,
            notifier=self._notifier,
            **isotp_params,
        )
        self._isotp_layer.start()

    def disconnect(self) -> None:
        """Close CAN connection and stop ISO-TP layer."""
        if self._isotp_layer is not None:
            self._isotp_layer.stop()
            self._isotp_layer = None

        if self._notifier is not None:
            self._notifier.stop()
            self._notifier = None

        if self._bus is not None:
            self._bus.shutdown()
            self._bus = None

    def send_recv(self, data: bytes, timeout: float = 5.0) -> bytes:
        """Send UDS request and receive response via CAN/ISO-TP.

        Args:
            data: UDS request bytes to send.
            timeout: Maximum time to wait for response in seconds.

        Returns:
            Response bytes from the target.

        Raises:
            ConnectionError: If not connected.
            TimeoutError: If no response received within timeout.
        """
        if self._isotp_layer is None:
            raise ConnectionError("Not connected")

        self._isotp_layer.send(data)
        response = self._isotp_layer.recv(timeout=timeout)

        if response is None:
            raise TimeoutError("No response received")

        return bytes(response)
