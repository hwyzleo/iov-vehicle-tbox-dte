"""Tests for UDS client wrapper."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dte.uds.client import UDSClient, UDSError, UDSResponse
from dte.uds.security import FixedKeyAdapter


class TestUDSResponse:
    """Tests for UDSResponse dataclass."""

    def test_positive_response(self):
        resp = UDSResponse(
            service_id=0x50,
            positive=True,
            data=b"\x01",
            raw=b"\x50\x01",
        )
        assert resp.positive is True
        assert resp.service_id == 0x50
        assert resp.data == b"\x01"
        assert resp.raw == b"\x50\x01"

    def test_negative_response(self):
        resp = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x10\x7F\x31",
            raw=b"\x7F\x10\x7F\x31",
            nrc=0x31,
        )
        assert resp.positive is False
        assert resp.nrc == 0x31


class TestUDSError:
    """Tests for UDSError exception."""

    def test_is_exception(self):
        assert issubclass(UDSError, Exception)

    def test_message(self):
        with pytest.raises(UDSError, match="test"):
            raise UDSError("test")


class TestUDSClientInit:
    """Tests for UDSClient initialization."""

    def test_default_init(self):
        client = UDSClient()
        assert client._conn is None
        assert client._security_adapter is None

    def test_init_with_connection(self):
        conn = MagicMock()
        client = UDSClient(conn=conn)
        assert client._conn is conn

    def test_init_with_security_adapter(self):
        adapter = FixedKeyAdapter(key=b"\xAA")
        client = UDSClient(security_adapter=adapter)
        assert client._security_adapter is adapter


class TestUDSClientConnection:
    """Tests for UDSClient connection management."""

    def test_set_connection(self):
        client = UDSClient()
        conn = MagicMock()
        client.set_connection(conn)
        assert client._conn is conn

    def test_context_manager_enter(self):
        conn = MagicMock()
        client = UDSClient(conn=conn)
        result = client.__enter__()
        assert result is client

    def test_context_manager_exit(self):
        mock_client = MagicMock()
        client = UDSClient()
        client._client = mock_client
        client.__exit__(None, None, None)
        mock_client.close.assert_called_once()

    def test_context_manager_exit_no_client(self):
        client = UDSClient()
        # Should not raise
        client.__exit__(None, None, None)


def _make_mock_udsoncan_response(valid=True, service_data=None, payload=b"\x50\x01"):
    """Create a mock udsoncan response."""
    response = MagicMock()
    response.valid = valid
    response.service_data = service_data or MagicMock()
    response.original_payload = payload
    return response


class TestUDSClientSessionControl:
    """Tests for UDSClient session_control (0x10)."""

    @patch("dte.uds.client.UdsClient")
    def test_session_control_default_session(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x50\x01"
        )
        mock_client.change_session.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.session_control(0x01)

        assert result.positive is True
        assert result.service_id == 0x50
        mock_client.change_session.assert_called_once_with(0x01)

    def test_session_control_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.session_control(0x01)


class TestUDSClientReadDID:
    """Tests for UDSClient read_did (0x22)."""

    @patch("dte.uds.client.UdsClient")
    def test_read_did_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x62\xF1\x90VIN123"
        )
        mock_client.read_data_by_identifier.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.read_did(0xF190)

        assert result.positive is True
        assert result.service_id == 0x62
        mock_client.read_data_by_identifier.assert_called_once_with(0xF190)

    def test_read_did_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.read_did(0xF190)


class TestUDSClientWriteDID:
    """Tests for UDSClient write_did (0x2E)."""

    @patch("dte.uds.client.UdsClient")
    def test_write_did_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x6E\xF1\x90"
        )
        mock_client.write_data_by_identifier.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.write_did(0xF190, b"VIN123")

        assert result.positive is True
        assert result.service_id == 0x6E
        mock_client.write_data_by_identifier.assert_called_once_with(0xF190, b"VIN123")

    def test_write_did_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.write_did(0xF190, b"VIN123")


class TestUDSClientSecurityAccess:
    """Tests for UDSClient security_access (0x27)."""

    @patch("dte.uds.client.UdsClient")
    def test_security_access_with_adapter(self, mock_client_class):
        mock_client = MagicMock()

        seed_data = MagicMock()
        seed_data.seed = b"\x12\x34"
        seed_response = _make_mock_udsoncan_response(
            valid=True, service_data=seed_data, payload=b"\x67\x01\x12\x34"
        )

        key_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x67\x02"
        )

        mock_client.request_seed.return_value = seed_response
        mock_client.send_key.return_value = key_response
        mock_client_class.return_value = mock_client

        adapter = FixedKeyAdapter(key=b"\x00\x00")
        client = UDSClient(conn=MagicMock(), security_adapter=adapter)
        result = client.security_access(0x01)

        assert result.positive is True
        mock_client.request_seed.assert_called_once_with(0x01, data=b"")
        mock_client.send_key.assert_called_once_with(0x02, b"\x00\x00")

    def test_security_access_no_adapter(self):
        client = UDSClient(conn=MagicMock())
        with pytest.raises(UDSError, match="No security adapter"):
            client.security_access(0x01)

    def test_security_access_not_connected(self):
        adapter = FixedKeyAdapter(key=b"\x00\x00")
        client = UDSClient(security_adapter=adapter)
        with pytest.raises(UDSError, match="Not connected"):
            client.security_access(0x01)


class TestUDSClientRoutineControl:
    """Tests for UDSClient routine_control (0x31)."""

    @patch("dte.uds.client.UdsClient")
    def test_routine_control_start(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x71\x01\xFF\x00"
        )
        mock_client.start_routine.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.routine_control(0xFF00, 0x01)

        assert result.positive is True
        assert result.service_id == 0x71
        mock_client.start_routine.assert_called_once_with(0xFF00, data=None)

    def test_routine_control_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.routine_control(0xFF00, 0x01)


class TestUDSClientReadDTC:
    """Tests for UDSClient read_dtc (0x19)."""

    @patch("dte.uds.client.UdsClient")
    def test_read_dtc_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x59\x02\xFF"
        )
        mock_client.get_dtc_by_status_mask.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.read_dtc(0x02)

        assert result.positive is True
        assert result.service_id == 0x59
        mock_client.get_dtc_by_status_mask.assert_called_once_with(0xFF)

    def test_read_dtc_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.read_dtc(0x02)


class TestUDSClientClearDTC:
    """Tests for UDSClient clear_dtc (0x14)."""

    @patch("dte.uds.client.UdsClient")
    def test_clear_dtc_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x54"
        )
        mock_client.clear_dtc.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.clear_dtc(0xFFFFFF)

        assert result.positive is True
        assert result.service_id == 0x54
        mock_client.clear_dtc.assert_called_once_with(0xFFFFFF)

    def test_clear_dtc_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.clear_dtc(0xFFFFFF)


class TestUDSClientIOControl:
    """Tests for UDSClient io_control (0x2F)."""

    @patch("dte.uds.client.UdsClient")
    def test_io_control_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = _make_mock_udsoncan_response(
            valid=True, payload=b"\x6F\x01\x00"
        )
        mock_client.io_control.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = UDSClient(conn=MagicMock())
        result = client.io_control(0x0100, control_type=0x03)

        assert result.positive is True
        assert result.service_id == 0x6F
        mock_client.io_control.assert_called_once_with(
            0x0100, control_param=0x03, values=None, masks=None
        )

    def test_io_control_not_connected(self):
        client = UDSClient()
        with pytest.raises(UDSError, match="Not connected"):
            client.io_control(0x0100)
