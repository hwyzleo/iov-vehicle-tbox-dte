"""Transport factory for creating transport instances from profiles."""
from __future__ import annotations

from dte.config.transport_profile import TransportProfile, TransportType

from .base import BaseTransport
from .can import CANTransport
from .doip import DoIPTransport


def create_transport(profile: TransportProfile) -> BaseTransport:
    """Create a transport instance from a transport profile.

    Args:
        profile: Transport profile configuration.

    Returns:
        Configured transport instance.

    Raises:
        ValueError: If transport type is unsupported.
    """
    if profile.transport_type == TransportType.DOIP:
        return DoIPTransport(config=profile.doip, profile=profile)
    elif profile.transport_type == TransportType.CAN:
        return CANTransport(config=profile.can, profile=profile)
    else:
        raise ValueError(f"Unsupported transport type: {profile.transport_type}")
