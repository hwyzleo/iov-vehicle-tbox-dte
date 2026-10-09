"""Security access adapters for UDS 0x27 service.

Provides pluggable seed-to-key conversion strategies for security access.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


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


class AES128ECBAdapter(SecurityAccessAdapter):
    """Computes key as AES-128-ECB(shared_secret, seed).

    Matches the TBOX SEC service seed-to-key algorithm
    (``SecService::compute_expected_key``, TBOX-SEC-DSN-CR-003 §5)::

        key = AES-128-ECB-Encrypt(key=shared_secret, plaintext=seed)

    Both seed and key are a single 16-byte block, no padding. The shared
    secret is provisioned on the device as ``sec.seed_key.shared_secret``
    (32 hex characters).
    """

    BLOCK_SIZE = 16

    def __init__(self, shared_secret: bytes) -> None:
        if len(shared_secret) != self.BLOCK_SIZE:
            raise SecurityAccessError(
                f"shared_secret must be {self.BLOCK_SIZE} bytes "
                f"(32 hex chars), got {len(shared_secret)}"
            )
        self._secret = shared_secret

    @classmethod
    def from_hex(cls, secret_hex: str) -> AES128ECBAdapter:
        """Build an adapter from a 32-character hex string."""
        try:
            secret = bytes.fromhex(secret_hex.strip())
        except ValueError as e:
            raise SecurityAccessError(f"shared_secret is not valid hex: {e}") from e
        return cls(secret)

    def compute_key(self, seed: bytes, level: int) -> bytes:
        """Encrypt the seed with AES-128-ECB under the shared secret."""
        if len(seed) != self.BLOCK_SIZE:
            raise SecurityAccessError(
                f"seed must be {self.BLOCK_SIZE} bytes, got {len(seed)}"
            )
        encryptor = Cipher(algorithms.AES(self._secret), modes.ECB()).encryptor()
        return encryptor.update(seed) + encryptor.finalize()


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
        adapter_type: Type of adapter ("fixed", "xor", "aes128ecb", or "callable").
        key: Key bytes. For "aes128ecb" this is the 16-byte shared secret.
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
    elif adapter_type == "aes128ecb":
        return AES128ECBAdapter(shared_secret=key)
    elif adapter_type == "callable":
        if fn is None:
            raise ValueError("fn parameter is required for callable adapter")
        return CallableAdapter(fn=fn)
    else:
        raise ValueError(
            f"Invalid adapter_type: {adapter_type}. "
            "Must be 'fixed', 'xor', 'aes128ecb', or 'callable'"
        )
