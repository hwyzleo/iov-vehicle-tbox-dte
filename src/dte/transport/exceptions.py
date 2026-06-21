"""Custom exceptions for transport layer."""
from __future__ import annotations


class TransportError(Exception):
    """Base exception for all transport-related errors."""


class ConnectionError(TransportError):
    """Raised when a connection operation fails."""


class TimeoutError(TransportError):
    """Raised when an operation times out."""
