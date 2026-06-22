"""Tests for TransportProfile configuration."""
from dataclasses import FrozenInstanceError

import pytest

from dte.config.transport_profile import (
    CANAddressing,
    CANConfig,
    DoIPConfig,
    TimingConfig,
    TransportProfile,
    TransportType,
)


class TestTransportType:
    """Tests for TransportType enum."""

    def test_doip_value(self):
        assert TransportType.DOIP.value == "doip"

    def test_can_value(self):
        assert TransportType.CAN.value == "can"

    def test_from_string(self):
        assert TransportType("doip") == TransportType.DOIP
        assert TransportType("can") == TransportType.CAN


class TestCANAddressing:
    """Tests for CANAddressing enum."""

    def test_values(self):
        assert CANAddressing.NORMAL.value == "normal"
        assert CANAddressing.EXTENDED.value == "extended"
        assert CANAddressing.MIXED.value == "mixed"


class TestDoIPConfig:
    """Tests for DoIPConfig dataclass."""

    def test_default_values(self):
        config = DoIPConfig()
        assert config.target_ip == "localhost"
        assert config.tcp_port == 13400
        assert config.udp_port == 13400
        assert config.source_addr == 0x0E00
        assert config.target_addr == 0x0001
        assert config.activation_type == 0x00
        assert config.discovery is True

    def test_custom_values(self):
        config = DoIPConfig(
            target_ip="192.168.1.100",
            tcp_port=13401,
            udp_port=13402,
            source_addr=0x1234,
            target_addr=0x5678,
            activation_type=0x01,
            discovery=False,
        )
        assert config.target_ip == "192.168.1.100"
        assert config.tcp_port == 13401
        assert config.udp_port == 13402
        assert config.source_addr == 0x1234
        assert config.target_addr == 0x5678
        assert config.activation_type == 0x01
        assert config.discovery is False

    def test_immutability(self):
        config = DoIPConfig()
        with pytest.raises(FrozenInstanceError):
            config.target_ip = "new_host"


class TestCANConfig:
    """Tests for CANConfig dataclass."""

    def test_default_values(self):
        config = CANConfig()
        assert config.interface == "socketcan"
        assert config.channel == "can0"
        assert config.bitrate == 500000
        assert config.addressing == CANAddressing.NORMAL
        assert config.req_id == 0x7E0
        assert config.resp_id == 0x7E8
        assert config.func_id == 0x7DF
        assert config.block_size == 0
        assert config.st_min == 0

    def test_custom_values(self):
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
        assert config.interface == "pcan"
        assert config.channel == "PCAN_USBBUS1"
        assert config.bitrate == 250000
        assert config.addressing == CANAddressing.EXTENDED
        assert config.req_id == 0x100
        assert config.resp_id == 0x101
        assert config.func_id == 0x102
        assert config.block_size == 8
        assert config.st_min == 10

    def test_immutability(self):
        config = CANConfig()
        with pytest.raises(FrozenInstanceError):
            config.channel = "can1"


class TestTimingConfig:
    """Tests for TimingConfig dataclass."""

    def test_default_values(self):
        config = TimingConfig()
        assert config.p2 == 5.0
        assert config.p2_star == 5.0
        assert config.n_as == 1.0
        assert config.n_ar == 1.0
        assert config.n_bs == 1.0
        assert config.n_cr == 1.0

    def test_custom_values(self):
        config = TimingConfig(
            p2=10.0,
            p2_star=100.0,
            n_as=2.0,
            n_ar=2.0,
            n_bs=2.0,
            n_cr=2.0,
        )
        assert config.p2 == 10.0
        assert config.p2_star == 100.0
        assert config.n_as == 2.0
        assert config.n_ar == 2.0
        assert config.n_bs == 2.0
        assert config.n_cr == 2.0

    def test_immutability(self):
        config = TimingConfig()
        with pytest.raises(FrozenInstanceError):
            config.p2 = 99.0


class TestTransportProfile:
    """Tests for TransportProfile dataclass."""

    def test_default_profile(self):
        profile = TransportProfile(name="test")
        assert profile.name == "test"
        assert profile.transport_type == TransportType.DOIP
        assert isinstance(profile.doip, DoIPConfig)
        assert isinstance(profile.can, CANConfig)
        assert isinstance(profile.timing, TimingConfig)

    def test_doip_profile(self):
        doip_config = DoIPConfig(target_ip="10.0.0.1", tcp_port=13401)
        profile = TransportProfile(
            name="doip_test",
            transport_type=TransportType.DOIP,
            doip=doip_config,
        )
        assert profile.name == "doip_test"
        assert profile.transport_type == TransportType.DOIP
        assert profile.doip.target_ip == "10.0.0.1"
        assert profile.doip.tcp_port == 13401

    def test_can_profile(self):
        can_config = CANConfig(interface="pcan", channel="PCAN_USBBUS1")
        profile = TransportProfile(
            name="can_test",
            transport_type=TransportType.CAN,
            can=can_config,
        )
        assert profile.name == "can_test"
        assert profile.transport_type == TransportType.CAN
        assert profile.can.interface == "pcan"
        assert profile.can.channel == "PCAN_USBBUS1"

    def test_full_profile(self):
        profile = TransportProfile(
            name="full_test",
            transport_type=TransportType.DOIP,
            doip=DoIPConfig(target_ip="192.168.0.1"),
            can=CANConfig(interface="vector"),
            timing=TimingConfig(p2=3.0),
        )
        assert profile.name == "full_test"
        assert profile.doip.target_ip == "192.168.0.1"
        assert profile.can.interface == "vector"
        assert profile.timing.p2 == 3.0

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
            "doip": {"target_ip": "10.0.0.1", "tcp_port": 13401},
            "can": {"interface": "pcan", "channel": "can1"},
            "timing": {"p2": 3.0},
        }
        profile = TransportProfile.from_dict(data)
        assert profile.name == "from_dict"
        assert profile.transport_type == TransportType.CAN
        assert profile.doip.target_ip == "10.0.0.1"
        assert profile.can.interface == "pcan"
        assert profile.timing.p2 == 3.0

    def test_from_dict_minimal(self):
        data = {"name": "minimal"}
        profile = TransportProfile.from_dict(data)
        assert profile.name == "minimal"
        assert profile.transport_type == TransportType.DOIP
        assert isinstance(profile.doip, DoIPConfig)

    def test_validate_valid_doip(self):
        profile = TransportProfile(name="test", transport_type=TransportType.DOIP)
        assert profile.validate() == []

    def test_validate_valid_can(self):
        profile = TransportProfile(name="test", transport_type=TransportType.CAN)
        assert profile.validate() == []

    def test_validate_empty_name(self):
        profile = TransportProfile(name="")
        errors = profile.validate()
        assert any("name" in e for e in errors)

    def test_validate_doip_missing_target_ip(self):
        profile = TransportProfile(
            name="test",
            transport_type=TransportType.DOIP,
            doip=DoIPConfig(target_ip=""),
        )
        errors = profile.validate()
        assert any("target_ip" in e for e in errors)

    def test_validate_doip_invalid_port(self):
        profile = TransportProfile(
            name="test",
            transport_type=TransportType.DOIP,
            doip=DoIPConfig(tcp_port=99999),
        )
        errors = profile.validate()
        assert any("tcp_port" in e for e in errors)

    def test_validate_can_missing_channel(self):
        profile = TransportProfile(
            name="test",
            transport_type=TransportType.CAN,
            can=CANConfig(channel=""),
        )
        errors = profile.validate()
        assert any("channel" in e for e in errors)

    def test_validate_negative_timing(self):
        profile = TransportProfile(
            name="test",
            timing=TimingConfig(p2=-1.0),
        )
        errors = profile.validate()
        assert any("p2" in e for e in errors)
