"""Tests for TransportProfile configuration."""
import pytest
from dataclasses import FrozenInstanceError

from dte.config.transport_profile import (
    TransportProfile,
    DoIPConfig,
    CANConfig,
    TimingConfig,
)


class TestDoIPConfig:
    """Tests for DoIPConfig dataclass."""

    def test_default_values(self):
        config = DoIPConfig()
        assert config.host == "localhost"
        assert config.port == 13400
        assert config.source_address == 0x0E00
        assert config.target_address == 0x0001
        assert config.timeout == 5.0

    def test_custom_values(self):
        config = DoIPConfig(
            host="192.168.1.100",
            port = 13401,
            source_address=0x1234,
            target_address=0x5678,
            timeout=10.0,
        )
        assert config.host == "192.168.1.100"
        assert config.port == 13401
        assert config.source_address == 0x1234
        assert config.target_address == 0x5678
        assert config.timeout == 10.0

    def test_immutability(self):
        config = DoIPConfig()
        with pytest.raises(FrozenInstanceError):
            config.host = "new_host"


class TestCANConfig:
    """Tests for CANConfig dataclass."""

    def test_default_values(self):
        config = CANConfig()
        assert config.interface == "socketcan"
        assert config.channel == "can0"
        assert config.bitrate == 500000
        assert config.fd is False
        assert config.data_bitrate == 2000000

    def test_custom_values(self):
        config = CANConfig(
            interface="pcan",
            channel="PCAN_USBBUS1",
            bitrate=250000,
            fd=True,
            data_bitrate=5000000,
        )
        assert config.interface == "pcan"
        assert config.channel == "PCAN_USBBUS1"
        assert config.bitrate == 250000
        assert config.fd is True
        assert config.data_bitrate == 5000000

    def test_immutability(self):
        config = CANConfig()
        with pytest.raises(FrozenInstanceError):
            config.channel = "can1"


class TestTimingConfig:
    """Tests for TimingConfig dataclass."""

    def test_default_values(self):
        config = TimingConfig()
        assert config.p2_client == 5.0
        assert config.p2_star_client == 50.0
        assert config.s3_client == 2.0

    def test_custom_values(self):
        config = TimingConfig(
            p2_client=10.0,
            p2_star_client=100.0,
            s3_client=5.0,
        )
        assert config.p2_client == 10.0
        assert config.p2_star_client == 100.0
        assert config.s3_client == 5.0

    def test_immutability(self):
        config = TimingConfig()
        with pytest.raises(FrozenInstanceError):
            config.p2_client = 99.0


class TestTransportProfile:
    """Tests for TransportProfile dataclass."""

    def test_default_profile(self):
        profile = TransportProfile(name="test")
        assert profile.name == "test"
        assert profile.transport_type == "doip"
        assert isinstance(profile.doip, DoIPConfig)
        assert isinstance(profile.can, CANConfig)
        assert isinstance(profile.timing, TimingConfig)

    def test_doip_profile(self):
        doip_config = DoIPConfig(host="10.0.0.1", port=13401)
        profile = TransportProfile(
            name="doip_test",
            transport_type="doip",
            doip=doip_config,
        )
        assert profile.name == "doip_test"
        assert profile.transport_type == "doip"
        assert profile.doip.host == "10.0.0.1"
        assert profile.doip.port == 13401

    def test_can_profile(self):
        can_config = CANConfig(interface="pcan", channel="PCAN_USBBUS1")
        profile = TransportProfile(
            name="can_test",
            transport_type="can",
            can=can_config,
        )
        assert profile.name == "can_test"
        assert profile.transport_type == "can"
        assert profile.can.interface == "pcan"
        assert profile.can.channel == "PCAN_USBBUS1"

    def test_full_profile(self):
        profile = TransportProfile(
            name="full_test",
            transport_type="doip",
            doip=DoIPConfig(host="192.168.0.1"),
            can=CANConfig(interface="vector"),
            timing=TimingConfig(p2_client=3.0),
        )
        assert profile.name == "full_test"
        assert profile.doip.host == "192.168.0.1"
        assert profile.can.interface == "vector"
        assert profile.timing.p2_client == 3.0

    def test_immutability(self):
        profile = TransportProfile(name="test")
        with pytest.raises(FrozenInstanceError):
            profile.name = "new_name"

    def test_to_dict(self):
        profile = TransportProfile(name="test")
        result = profile.to_dict()
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["transport_type"] == "doip"
        assert "doip" in result
        assert "can" in result
        assert "timing" in result

    def test_from_dict(self):
        data = {
            "name": "from_dict",
            "transport_type": "can",
            "doip": {"host": "10.0.0.1", "port": 13401},
            "can": {"interface": "pcan", "channel": "can1"},
            "timing": {"p2_client": 3.0},
        }
        profile = TransportProfile.from_dict(data)
        assert profile.name == "from_dict"
        assert profile.transport_type == "can"
        assert profile.doip.host == "10.0.0.1"
        assert profile.can.interface == "pcan"
        assert profile.timing.p2_client == 3.0

    def test_from_dict_minimal(self):
        data = {"name": "minimal"}
        profile = TransportProfile.from_dict(data)
        assert profile.name == "minimal"
        assert profile.transport_type == "doip"
        assert isinstance(profile.doip, DoIPConfig)
