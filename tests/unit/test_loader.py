"""Tests for configuration loader."""
import json
from pathlib import Path

import pytest

from dte.config.loader import ConfigLoaderError, load_config
from dte.config.transport_profile import TransportProfile, TransportType


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_yaml(self, tmp_path):
        yaml_content = """
profiles:
  test_profile:
    transport_type: doip
    doip:
      target_ip: 192.168.1.100
      tcp_port: 13401
    timing:
      p2: 3.0
"""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        assert "test_profile" in profiles
        profile = profiles["test_profile"]
        assert isinstance(profile, TransportProfile)
        assert profile.name == "test_profile"
        assert profile.transport_type == TransportType.DOIP
        assert profile.doip.target_ip == "192.168.1.100"
        assert profile.timing.p2 == 3.0

    def test_load_yml_extension(self, tmp_path):
        yaml_content = """
profiles:
  test:
    transport_type: doip
"""
        config_file = tmp_path / "test.yml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        assert "test" in profiles

    def test_load_json(self, tmp_path):
        json_content = {
            "profiles": {
                "test_profile": {
                    "transport_type": "can",
                    "can": {
                        "interface": "pcan",
                        "channel": "can0",
                    },
                }
            }
        }
        config_file = tmp_path / "test.json"
        config_file.write_text(json.dumps(json_content))

        profiles = load_config(config_file)
        assert "test_profile" in profiles
        profile = profiles["test_profile"]
        assert profile.transport_type == TransportType.CAN
        assert profile.can.interface == "pcan"

    def test_load_multiple_profiles(self, tmp_path):
        yaml_content = """
profiles:
  profile1:
    transport_type: doip
    doip:
      target_ip: 10.0.0.1
  profile2:
    transport_type: can
    can:
      interface: vector
"""
        config_file = tmp_path / "multi.yaml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        assert len(profiles) == 2
        assert "profile1" in profiles
        assert "profile2" in profiles

    def test_load_empty_profiles(self, tmp_path):
        yaml_content = """
profiles: {}
"""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        assert len(profiles) == 0

    def test_load_full_doip_config(self, tmp_path):
        yaml_content = """
profiles:
  full_doip:
    transport_type: doip
    doip:
      target_ip: 192.168.1.100
      tcp_port: 13401
      udp_port: 13402
      source_addr: 4096
      target_addr: 1
      activation_type: 0
      discovery: true
"""
        config_file = tmp_path / "full_doip.yaml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        profile = profiles["full_doip"]
        assert profile.doip.target_ip == "192.168.1.100"
        assert profile.doip.tcp_port == 13401
        assert profile.doip.udp_port == 13402
        assert profile.doip.source_addr == 4096
        assert profile.doip.target_addr == 1
        assert profile.doip.activation_type == 0
        assert profile.doip.discovery is True

    def test_load_full_can_config(self, tmp_path):
        yaml_content = """
profiles:
  full_can:
    transport_type: can
    can:
      interface: pcan
      channel: PCAN_USBBUS1
      bitrate: 250000
      addressing: extended
      req_id: 256
      resp_id: 257
      func_id: 258
      block_size: 8
      st_min: 10
"""
        config_file = tmp_path / "full_can.yaml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        profile = profiles["full_can"]
        assert profile.can.interface == "pcan"
        assert profile.can.channel == "PCAN_USBBUS1"
        assert profile.can.bitrate == 250000
        assert profile.can.addressing.value == "extended"
        assert profile.can.req_id == 256
        assert profile.can.resp_id == 257
        assert profile.can.func_id == 258
        assert profile.can.block_size == 8
        assert profile.can.st_min == 10

    def test_load_full_timing_config(self, tmp_path):
        yaml_content = """
profiles:
  full_timing:
    transport_type: doip
    timing:
      p2: 10.0
      p2_star: 100.0
      n_as: 2.0
      n_ar: 2.0
      n_bs: 2.0
      n_cr: 2.0
"""
        config_file = tmp_path / "full_timing.yaml"
        config_file.write_text(yaml_content)

        profiles = load_config(config_file)
        profile = profiles["full_timing"]
        assert profile.timing.p2 == 10.0
        assert profile.timing.p2_star == 100.0
        assert profile.timing.n_as == 2.0
        assert profile.timing.n_ar == 2.0
        assert profile.timing.n_bs == 2.0
        assert profile.timing.n_cr == 2.0

    def test_file_not_found(self):
        with pytest.raises(ConfigLoaderError, match="not found"):
            load_config(Path("/nonexistent/config.yaml"))

    def test_invalid_yaml(self, tmp_path):
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("{{invalid yaml}}")

        with pytest.raises(ConfigLoaderError, match="Failed to parse"):
            load_config(config_file)

    def test_invalid_json(self, tmp_path):
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json}")

        with pytest.raises(ConfigLoaderError, match="Failed to parse"):
            load_config(config_file)

    def test_unsupported_format(self, tmp_path):
        config_file = tmp_path / "config.txt"
        config_file.write_text("some content")

        with pytest.raises(ConfigLoaderError, match="Unsupported"):
            load_config(config_file)

    def test_missing_profiles_key(self, tmp_path):
        yaml_content = """
some_key:
  value: 123
"""
        config_file = tmp_path / "no_profiles.yaml"
        config_file.write_text(yaml_content)

        with pytest.raises(ConfigLoaderError, match="Missing 'profiles'"):
            load_config(config_file)
