"""CAN/ISO-TP transport implementation."""
from __future__ import annotations

from typing import Optional

import can
import isotp

from dte.config.transport_profile import CANConfig

from .base import BaseTransport


class CANTransport(BaseTransport):
    """CAN/ISO-TP transport for diagnostic communication.

    Uses python-can for CAN bus access and can-isotp for
    ISO-TP (ISO 15765-2) segmentation.
    """

    def __init__(self, config: CANConfig) -> None:
        """Initialize CAN transport.

        Args:
            config: CAN configuration parameters.
        """
        self.config = config
        self._bus: Optional[can.BusABC] = None
        self._notifier: Optional[can.Notifier] = None
        self._isotp_layer: Optional[isotp.NotifierBasedCanStack] = None

    def connect(self) -> None:
        """Establish CAN connection and start ISO-TP layer."""
        self._bus = can.Bus(
            interface=self.config.interface,
            channel=self.config.channel,
            bitrate=self.config.bitrate,
        )

        self._notifier = can.Notifier(self._bus, [])

        isotp_params = {
            "txid": self.config.req_id,
            "rxid": self.config.resp_id,
            "block_size": self.config.block_size,
            "st_min": self.config.st_min,
        }

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
