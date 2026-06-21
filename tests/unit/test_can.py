"""Tests for CAN/ISO-TP transport implementation."""
from unittest.mock import MagicMock, patch

import pytest

from dte.config.transport_profile import CANAddressing, CANConfig, TransportProfile, TransportType
from dte.transport.can import CANTransport
from dte.transport.exceptions import ConnectionError, TimeoutError


class TestCANTransportInit:
    """Tests for CANTransport initialization."""

    def test_default_config(self):
        config = CANConfig()
        transport = CANTransport(config)
        assert transport.config == config
        assert transport._bus is None
        assert transport._isotp_layer is None

    def test_custom_config(self):
        config = CANConfig(
            interface="pcan",
            channel="PCAN_USBBUS1",
            bitrate=250000,
            addressing=CANAddressing.EXTENDED,
            req_id=0x100,
            resp_id=0x101,
            func_id=0x102,
            block_size=8,
            st_min=10,
        )
        transport = CANTransport(config)
        assert transport.config.interface == "pcan"
        assert transport.config.channel == "PCAN_USBBUS1"
        assert transport.config.bitrate == 250000
        assert transport.config.addressing == CANAddressing.EXTENDED
        assert transport.config.req_id == 0x100
        assert transport.config.resp_id == 0x101
        assert transport.config.func_id == 0x102
        assert transport.config.block_size == 8
        assert transport.config.st_min == 10

    def test_profile_property_with_profile(self):
        config = CANConfig()
        profile = TransportProfile(name="test", transport_type=TransportType.CAN)
        transport = CANTransport(config, profile=profile)
        assert transport.profile == profile

    def test_profile_property_without_profile(self):
        config = CANConfig()
        transport = CANTransport(config)
        with pytest.raises(AttributeError, match="No profile configured"):
            _ = transport.profile

    def test_is_connected_when_disconnected(self):
        config = CANConfig()
        transport = CANTransport(config)
        assert transport.is_connected is False

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_is_connected_when_connected(self, mock_can, mock_isotp):
        mock_can.Bus.return_value = MagicMock()
        mock_can.Notifier.return_value = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = MagicMock()

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()
        assert transport.is_connected is True


class TestCANTransportConnect:
    """Tests for CANTransport connect method."""

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_connect_success(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()

        mock_can.Bus.assert_called_once_with(
            interface="socketcan",
            channel="can0",
            bitrate=500000,
        )
        mock_can.Notifier.assert_called_once_with(mock_bus, [])
        mock_isotp.NotifierBasedCanStack.assert_called_once_with(
            bus=mock_bus,
            notifier=mock_notifier,
            txid=0x7E0,
            rxid=0x7E8,
            block_size=0,
            st_min=0,
        )
        mock_layer.start.assert_called_once()
        assert transport._bus == mock_bus
        assert transport._notifier == mock_notifier
        assert transport._isotp_layer == mock_layer

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_connect_with_custom_config(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig(
            interface="pcan",
            channel="PCAN_USBBUS1",
            bitrate=250000,
            req_id=0x100,
            resp_id=0x101,
            block_size=8,
            st_min=10,
        )
        transport = CANTransport(config)
        transport.connect()

        mock_can.Bus.assert_called_once_with(
            interface="pcan",
            channel="PCAN_USBBUS1",
            bitrate=250000,
        )
        mock_can.Notifier.assert_called_once_with(mock_bus, [])
        mock_isotp.NotifierBasedCanStack.assert_called_once_with(
            bus=mock_bus,
            notifier=mock_notifier,
            txid=0x100,
            rxid=0x101,
            block_size=8,
            st_min=10,
        )

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_connect_extended_addressing(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig(
            addressing=CANAddressing.EXTENDED,
            req_id=0x100,
            resp_id=0x101,
        )
        transport = CANTransport(config)
        transport.connect()

        mock_isotp.NotifierBasedCanStack.assert_called_once_with(
            bus=mock_bus,
            notifier=mock_notifier,
            txid=0x100,
            rxid=0x101,
            block_size=0,
            st_min=0,
            addressing_mode=mock_isotp.AddressingMode.Extended,
        )

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_connect_mixed_addressing(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig(
            addressing=CANAddressing.MIXED,
            req_id=0x100,
            resp_id=0x101,
        )
        transport = CANTransport(config)
        transport.connect()

        mock_isotp.NotifierBasedCanStack.assert_called_once_with(
            bus=mock_bus,
            notifier=mock_notifier,
            txid=0x100,
            rxid=0x101,
            block_size=0,
            st_min=0,
            addressing_mode=mock_isotp.AddressingMode.Mixed_29bits,
        )

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_connect_failure(self, mock_can, mock_isotp):
        mock_can.Bus.side_effect = Exception("CAN interface not found")

        config = CANConfig()
        transport = CANTransport(config)

        with pytest.raises(Exception, match="CAN interface not found"):
            transport.connect()

        assert transport._bus is None
        assert transport._notifier is None
        assert transport._isotp_layer is None


class TestCANTransportDisconnect:
    """Tests for CANTransport disconnect method."""

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_disconnect_when_connected(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()
        transport.disconnect()

        mock_layer.stop.assert_called_once()
        mock_notifier.stop.assert_called_once()
        mock_bus.shutdown.assert_called_once()
        assert transport._isotp_layer is None
        assert transport._notifier is None
        assert transport._bus is None

    def test_disconnect_when_not_connected(self):
        config = CANConfig()
        transport = CANTransport(config)
        # Should not raise
        transport.disconnect()
        assert transport._isotp_layer is None
        assert transport._notifier is None
        assert transport._bus is None


class TestCANTransportSendRecv:
    """Tests for CANTransport send_recv method."""

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_send_recv_success(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_layer.send.return_value = None
        mock_layer.recv.return_value = bytearray([0x50, 0x01])
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()

        response = transport.send_recv(bytes([0x10, 0x01]), timeout=5.0)

        mock_layer.send.assert_called_once_with(bytes([0x10, 0x01]))
        mock_layer.recv.assert_called_once_with(timeout=5.0)
        assert response == bytes([0x50, 0x01])

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_send_recv_default_timeout(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_layer.send.return_value = None
        mock_layer.recv.return_value = bytearray([0x50, 0x01])
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()

        transport.send_recv(bytes([0x10, 0x01]))

        mock_layer.send.assert_called_once_with(bytes([0x10, 0x01]))
        mock_layer.recv.assert_called_once_with(timeout=5.0)

    def test_send_recv_not_connected(self):
        config = CANConfig()
        transport = CANTransport(config)

        with pytest.raises(ConnectionError, match="Not connected"):
            transport.send_recv(bytes([0x10, 0x01]))

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_send_recv_timeout_error(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_layer.send.side_effect = TimeoutError("Send timed out")
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()

        with pytest.raises(TimeoutError, match="Send timed out"):
            transport.send_recv(bytes([0x10, 0x01]), timeout=1.0)

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_send_recv_recv_timeout(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_layer.send.return_value = None
        mock_layer.recv.return_value = None
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)
        transport.connect()

        with pytest.raises(TimeoutError, match="No response received"):
            transport.send_recv(bytes([0x10, 0x01]), timeout=1.0)


class TestCANTransportContextManager:
    """Tests for CANTransport context manager support."""

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_context_manager_enter(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)

        with transport as t:
            assert t == transport
            mock_can.Bus.assert_called_once()

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_context_manager_exit(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)

        with transport:
            pass

        mock_layer.stop.assert_called_once()
        mock_notifier.stop.assert_called_once()
        mock_bus.shutdown.assert_called_once()
        assert transport._isotp_layer is None
        assert transport._notifier is None
        assert transport._bus is None

    @patch("dte.transport.can.isotp")
    @patch("dte.transport.can.can")
    def test_context_manager_exit_on_exception(self, mock_can, mock_isotp):
        mock_bus = MagicMock()
        mock_can.Bus.return_value = mock_bus

        mock_notifier = MagicMock()
        mock_can.Notifier.return_value = mock_notifier

        mock_layer = MagicMock()
        mock_isotp.NotifierBasedCanStack.return_value = mock_layer

        config = CANConfig()
        transport = CANTransport(config)

        with pytest.raises(ValueError):
            with transport:
                raise ValueError("Test exception")

        mock_layer.stop.assert_called_once()
        mock_notifier.stop.assert_called_once()
        mock_bus.shutdown.assert_called_once()
        assert transport._isotp_layer is None
        assert transport._notifier is None
        assert transport._bus is None
