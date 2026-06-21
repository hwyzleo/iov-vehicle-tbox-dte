"""Test step model for DTE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StepRequest:
    """UDS request for a test step."""

    sid: int
    data: bytes
    did: int | None = None
    sub_function: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sid": self.sid,
            "data": self.data.hex(),
            "did": self.did,
            "sub_function": self.sub_function,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepRequest:
        """Create from dictionary."""
        return cls(
            sid=data["sid"],
            data=bytes.fromhex(data["data"]),
            did=data.get("did"),
            sub_function=data.get("sub_function"),
        )


@dataclass
class StepExpect:
    """Expected response for a test step."""

    positive: bool = True
    nrc: int | None = None
    data: bytes | None = None
    did: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "positive": self.positive,
            "nrc": self.nrc,
            "data": self.data.hex() if self.data else None,
            "did": self.did,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepExpect:
        """Create from dictionary."""
        raw_data = data.get("data")
        return cls(
            positive=data.get("positive", True),
            nrc=data.get("nrc"),
            data=bytes.fromhex(raw_data) if raw_data else None,
            did=data.get("did"),
        )


@dataclass
class TestStep:
    """A single test step with request and expected response."""

    name: str
    request: StepRequest
    expect: StepExpect
    on_fail: str = "abort"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "request": self.request.to_dict(),
            "expect": self.expect.to_dict(),
            "on_fail": self.on_fail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestStep:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            request=StepRequest.from_dict(data["request"]),
            expect=StepExpect.from_dict(data.get("expect", {})),
            on_fail=data.get("on_fail", "abort"),
        )
