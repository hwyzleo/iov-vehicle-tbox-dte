"""Tests for DoIP transport implementation."""
from unittest.mock import MagicMock, patch

import pytest

from dte.config.transport_profile import DoIPConfig
from dte.transport.doip import DoIPTransport


class TestDoIPTransportInit:
    """Tests for DoIPTransport initialization."""

    def test_default_config(self):
        config = DoIPConfig()
        transport = DoIPTransport(config)
        assert transport.config == config
        assert transport._client is None

    def test_custom_config(self):
        config = DoIPConfig(
            target_ip="192.168.1.100",
            tcp_port=13401,
            source_addr=0x1234,
            target_addr=0x5678,
        )
        transport = DoIPTransport(config)
        assert transport.config.target_ip == "192.168.1.100"
        assert transport.config.tcp_port == 13401
        assert transport.config.source_addr == 0x1234
        assert transport.config.target_addr == 0x5678


class TestDoIPTransportConnect:
    """Tests for DoIPTransport connect method."""

    @patch("dte.transport.doip.DoIPClient")
    def test_connect_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = DoIPConfig(target_ip="192.168.1.100")
        transport = DoIPTransport(config)
        transport.connect()

        mock_client_class.assert_called_once_with(
            "192.168.1.100",
            0x0010,
            tcp_port=13400,
            activation_type=0x00,
            client_logical_address=0x0E00,
        )
        assert transport._client == mock_client

    @patch("dte.transport.doip.DoIPClient")
    def test_connect_with_custom_config(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = DoIPConfig(
            target_ip="10.0.0.1",
            tcp_port=13401,
            udp_port=13402,
            source_addr=0x1234,
            target_addr=0x5678,
            activation_type=0x01,
        )
        transport = DoIPTransport(config)
        transport.connect()

        mock_client_class.assert_called_once_with(
            "10.0.0.1",
            0x5678,
            tcp_port=13401,
            activation_type=0x01,
            client_logical_address=0x1234,
        )

    @patch("dte.transport.doip.DoIPClient")
    def test_connect_failure(self, mock_client_class):
        mock_client_class.side_effect = ConnectionError("Connection refused")

        config = DoIPConfig()
        transport = DoIPTransport(config)

        with pytest.raises(ConnectionError, match="Connection refused"):
            transport.connect()

        assert transport._client is None


class TestDoIPTransportDisconnect:
    """Tests for DoIPTransport disconnect method."""

    @patch("dte.transport.doip.DoIPClient")
    def test_disconnect_when_connected(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)
        transport.connect()
        transport.disconnect()

        mock_client.close.assert_called_once()
        assert transport._client is None

    def test_disconnect_when_not_connected(self):
        config = DoIPConfig()
        transport = DoIPTransport(config)
        # Should not raise
        transport.disconnect()
        assert transport._client is None


class TestDoIPTransportSendRecv:
    """Tests for DoIPTransport send_recv method."""

    @patch("dte.transport.doip.DoIPClient")
    def test_send_recv_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.receive_diagnostic.return_value = bytearray([0x50, 0x01])
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)
        transport.connect()

        response = transport.send_recv(bytes([0x10, 0x01]), timeout=5.0)

        mock_client.send_diagnostic.assert_called_once_with(bytes([0x10, 0x01]), timeout=5.0)
        mock_client.receive_diagnostic.assert_called_once_with(timeout=5.0)
        assert response == bytes([0x50, 0x01])

    @patch("dte.transport.doip.DoIPClient")
    def test_send_recv_default_timeout(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.receive_diagnostic.return_value = bytearray([0x50, 0x01])
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)
        transport.connect()

        transport.send_recv(bytes([0x10, 0x01]))

        mock_client.send_diagnostic.assert_called_once_with(bytes([0x10, 0x01]), timeout=5.0)
        mock_client.receive_diagnostic.assert_called_once_with(timeout=5.0)

    def test_send_recv_not_connected(self):
        config = DoIPConfig()
        transport = DoIPTransport(config)

        with pytest.raises(ConnectionError, match="Not connected"):
            transport.send_recv(bytes([0x10, 0x01]))

    @patch("dte.transport.doip.DoIPClient")
    def test_send_recv_timeout_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.receive_diagnostic.side_effect = TimeoutError("Request timed out")
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)
        transport.connect()

        with pytest.raises(TimeoutError, match="Request timed out"):
            transport.send_recv(bytes([0x10, 0x01]), timeout=1.0)


class TestDoIPTransportContextManager:
    """Tests for DoIPTransport context manager support."""

    @patch("dte.transport.doip.DoIPClient")
    def test_context_manager_enter(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)

        with transport as t:
            assert t == transport
            mock_client_class.assert_called_once()

    @patch("dte.transport.doip.DoIPClient")
    def test_context_manager_exit(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)

        with transport:
            pass

        mock_client.close.assert_called_once()
        assert transport._client is None

    @patch("dte.transport.doip.DoIPClient")
    def test_context_manager_exit_on_exception(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        config = DoIPConfig()
        transport = DoIPTransport(config)

        with pytest.raises(ValueError):
            with transport:
                raise ValueError("Test exception")

        mock_client.close.assert_called_once()
        assert transport._client is None
