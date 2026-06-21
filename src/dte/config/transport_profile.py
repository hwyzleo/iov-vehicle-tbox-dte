"""Transport profile configuration for DTE."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class DoIPConfig:
    """DoIP (Diagnostics over IP) transport configuration."""

    host: str = "localhost"
    port: int = 13400
    source_address: int = 0x0E00
    target_address: int = 0x0001
    timeout: float = 5.0


@dataclass(frozen=True)
class CANConfig:
    """CAN bus transport configuration."""

    interface: str = "socketcan"
    channel: str = "can0"
    bitrate: int = 500000
    fd: bool = False
    data_bitrate: int = 2000000


@dataclass(frozen=True)
class TimingConfig:
    """Diagnostic timing parameters (in seconds)."""

    p2_client: float = 5.0
    p2_star_client: float = 50.0
    s3_client: float = 2.0


@dataclass(frozen=True)
class TransportProfile:
    """Complete transport profile for diagnostic communication.

    A profile encapsulates all configuration needed to establish
    a diagnostic session with a TBOX.
    """

    name: str
    transport_type: str = "doip"
    doip: DoIPConfig = field(default_factory=DoIPConfig)
    can: CANConfig = field(default_factory=CANConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TransportProfile:
        """Create profile from dictionary.

        Args:
            data: Dictionary with profile configuration.
                  Must contain 'name' key. Other keys are optional.

        Returns:
            TransportProfile instance.
        """
        doip_data = data.get("doip", {})
        can_data = data.get("can", {})
        timing_data = data.get("timing", {})

        return cls(
            name=data["name"],
            transport_type=data.get("transport_type", "doip"),
            doip=DoIPConfig(**doip_data) if doip_data else DoIPConfig(),
            can=CANConfig(**can_data) if can_data else CANConfig(),
            timing=TimingConfig(**timing_data) if timing_data else TimingConfig(),
        )
