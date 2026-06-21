"""Security access adapters for UDS 0x27 service.

Provides pluggable seed-to-key conversion strategies for security access.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class SecurityAccessError(Exception):
    """Raised when security access operations fail."""


class SecurityAccessAdapter(ABC):
    """Abstract base class for security access seed-to-key adapters.

    Subclasses must implement compute_key to convert a seed and
    security level into the corresponding key.
    """

    @abstractmethod
    def compute_key(self, seed: bytes, level: int) -> bytes:
        """Compute key from seed and security level.

        Args:
            seed: Seed bytes received from ECU.
            level: Security access level (odd = request seed, even = send key).

        Returns:
            Computed key bytes to send to ECU.
        """


class FixedKeyAdapter(SecurityAccessAdapter):
    """Returns a fixed key regardless of seed.

    Useful for ECUs that use a static key for security access.
    """

    def __init__(self, key: bytes) -> None:
        self._key = key

    @property
    def key(self) -> bytes:
        """Return the fixed key."""
        return self._key

    def compute_key(self, seed: bytes, level: int) -> bytes:
        """Return the fixed key, ignoring seed and level."""
        return self._key


class XORAdapter(SecurityAccessAdapter):
    """Computes key by XOR-ing seed with a configured key.

    If key is shorter than seed, key bytes are repeated cyclically.
    If key is longer than seed, only the needed key bytes are used.
    """

    def __init__(self, key: bytes) -> None:
        self._key = key

    def compute_key(self, seed: bytes, level: int) -> bytes:
        """XOR seed with key (repeated cyclically)."""
        if not self._key:
            return seed
        return bytes(s ^ self._key[i % len(self._key)] for i, s in enumerate(seed))


class CallableAdapter(SecurityAccessAdapter):
    """Delegates key computation to a user-provided callable.

    The callable receives (seed, level) and returns the key bytes.
    """

    def __init__(self, fn: Callable[[bytes, int], bytes]) -> None:
        self._fn = fn

    @property
    def callable(self) -> Callable[[bytes, int], bytes]:
        """Return the underlying callable."""
        return self._fn

    def compute_key(self, seed: bytes, level: int) -> bytes:
        """Delegate to the wrapped callable."""
        return self._fn(seed, level)


def create_adapter(
    adapter_type: str = "fixed",
    key: bytes = b"",
    fn: Callable[[bytes, int], bytes] | None = None,
) -> SecurityAccessAdapter:
    """Factory function to create security access adapters.

    Args:
        adapter_type: Type of adapter to create ("fixed", "xor", or "callable").
        key: Key bytes for fixed or XOR adapters.
        fn: Callable for callable adapter.

    Returns:
        Configured SecurityAccessAdapter instance.

    Raises:
        ValueError: If invalid adapter_type or missing required parameters.
    """
    if adapter_type == "fixed":
        return FixedKeyAdapter(key=key)
    elif adapter_type == "xor":
        return XORAdapter(key=key)
    elif adapter_type == "callable":
        if fn is None:
            raise ValueError("fn parameter is required for callable adapter")
        return CallableAdapter(fn=fn)
    else:
        raise ValueError(
            f"Invalid adapter_type: {adapter_type}. Must be 'fixed', 'xor', or 'callable'"
        )
