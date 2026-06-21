"""Configuration file loader for DTE."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from dte.config.transport_profile import TransportProfile


class ConfigLoaderError(Exception):
    """Raised when configuration loading fails."""


def load_config(path: Path) -> dict[str, TransportProfile]:
    """Load transport profiles from a configuration file.

    Supports YAML (.yaml, .yml) and JSON (.json) formats.

    The file must contain a 'profiles' key mapping profile names
    to their configuration.

    Example YAML:
        ```yaml
        profiles:
          eol_test:
            transport_type: doip
            doip:
              host: 192.168.1.100
              port: 13401
        ```

    Args:
        path: Path to configuration file.

    Returns:
        Dictionary mapping profile names to TransportProfile instances.

    Raises:
        ConfigLoaderError: If file not found, invalid format, or parse error.
    """
    path = Path(path)

    if not path.exists():
        raise ConfigLoaderError(f"Configuration file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        data = _load_yaml(path)
    elif suffix == ".json":
        data = _load_json(path)
    else:
        raise ConfigLoaderError(
            f"Unsupported file format: {suffix}. Use .yaml, .yml, or .json"
        )

    return _parse_profiles(data)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse YAML file."""
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigLoaderError(f"Failed to parse YAML file: {e}") from e


def _load_json(path: Path) -> dict[str, Any]:
    """Load and parse JSON file."""
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigLoaderError(f"Failed to parse JSON file: {e}") from e


def _parse_profiles(data: dict[str, Any]) -> dict[str, TransportProfile]:
    """Parse profiles from loaded data."""
    if "profiles" not in data:
        raise ConfigLoaderError(
            "Missing 'profiles' key in configuration file"
        )

    profiles = {}
    for name, config in data["profiles"].items():
        config["name"] = name
        profiles[name] = TransportProfile.from_dict(config)

    return profiles
