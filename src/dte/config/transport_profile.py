"""Transport profile configuration for DTE."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TransportType(str, Enum):
    """Supported transport types."""

    DOIP = "doip"
    CAN = "can"


class CANAddressing(str, Enum):
    """CAN addressing modes."""

    NORMAL = "normal"
    EXTENDED = "extended"
    MIXED = "mixed"


@dataclass(frozen=True)
class DoIPConfig:
    """DoIP (Diagnostics over IP) transport configuration."""

    target_ip: str = "localhost"
    tcp_port: int = 13400
    udp_port: int = 13400
    source_addr: int = 0x0E00
    target_addr: int = 0x0001
    activation_type: int = 0x00
    discovery: bool = True


@dataclass(frozen=True)
class CANConfig:
    """CAN bus transport configuration."""

    interface: str = "socketcan"
    channel: str = "can0"
    bitrate: int = 500000
    addressing: CANAddressing = CANAddressing.NORMAL
    req_id: int = 0x7E0
    resp_id: int = 0x7E8
    func_id: int = 0x7DF
    block_size: int = 0
    st_min: int = 0


@dataclass(frozen=True)
class TimingConfig:
    """Diagnostic timing parameters (in seconds)."""

    p2: float = 5.0
    p2_star: float = 50.0
    n_as: float = 1.0
    n_ar: float = 1.0
    n_bs: float = 1.0
    n_cr: float = 1.0


@dataclass(frozen=True)
class TransportProfile:
    """Complete transport profile for diagnostic communication.

    A profile encapsulates all configuration needed to establish
    a diagnostic session with a TBOX.
    """

    name: str
    transport_type: TransportType = TransportType.DOIP
    doip: DoIPConfig = field(default_factory=DoIPConfig)
    can: CANConfig = field(default_factory=CANConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)

    def validate(self) -> list[str]:
        """Validate the transport profile configuration.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors: list[str] = []

        if not self.name:
            errors.append("Profile name is required")

        if self.transport_type == TransportType.DOIP:
            if not self.doip.target_ip:
                errors.append("DoIP target_ip is required for DoIP transport")
            if not (0 <= self.doip.tcp_port <= 65535):
                errors.append(f"DoIP tcp_port out of range: {self.doip.tcp_port}")
            if not (0 <= self.doip.udp_port <= 65535):
                errors.append(f"DoIP udp_port out of range: {self.doip.udp_port}")

        if self.transport_type == TransportType.CAN:
            if not self.can.channel:
                errors.append("CAN channel is required for CAN transport")
            if self.can.req_id < 0:
                errors.append(f"CAN req_id must be non-negative: {self.can.req_id}")
            if self.can.resp_id < 0:
                errors.append(f"CAN resp_id must be non-negative: {self.can.resp_id}")

        if self.timing.p2 < 0:
            errors.append(f"Timing p2 must be non-negative: {self.timing.p2}")
        if self.timing.p2_star < 0:
            errors.append(f"Timing p2_star must be non-negative: {self.timing.p2_star}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        d = asdict(self)
        d["transport_type"] = self.transport_type.value
        d["can"]["addressing"] = self.can.addressing.value
        return d

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

        transport_type = data.get("transport_type", "doip")
        if isinstance(transport_type, str):
            transport_type = TransportType(transport_type)

        if can_data and "addressing" in can_data:
            addr = can_data["addressing"]
            if isinstance(addr, str):
                can_data["addressing"] = CANAddressing(addr)

        return cls(
            name=data["name"],
            transport_type=transport_type,
            doip=DoIPConfig(**doip_data) if doip_data else DoIPConfig(),
            can=CANConfig(**can_data) if can_data else CANConfig(),
            timing=TimingConfig(**timing_data) if timing_data else TimingConfig(),
        )
