"""Test step model for DTE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StepRequest:
    """UDS request for a test step."""

    service: int
    data: bytes
    routine_id: int | None = None
    control_type: int | None = None
    sub_function: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service": self.service,
            "data": self.data.hex(),
            "routine_id": self.routine_id,
            "control_type": self.control_type,
            "sub_function": self.sub_function,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepRequest:
        """Create from dictionary."""
        return cls(
            service=data["service"],
            data=bytes.fromhex(data["data"]),
            routine_id=data.get("routine_id"),
            control_type=data.get("control_type"),
            sub_function=data.get("sub_function"),
        )


@dataclass
class StepExpect:
    """Expected response for a test step."""

    success: bool = True
    nrc: int | None = None
    did_data_match: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "nrc": self.nrc,
            "did_data_match": self.did_data_match,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepExpect:
        """Create from dictionary."""
        return cls(
            success=data.get("success", True),
            nrc=data.get("nrc"),
            did_data_match=data.get("did_data_match"),
        )


@dataclass
class TestStep:
    """A single test step with request and expected response."""

    id: str
    request: StepRequest
    expect: StepExpect
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "request": self.request.to_dict(),
            "expect": self.expect.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestStep:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data.get("description"),
            request=StepRequest.from_dict(data["request"]),
            expect=StepExpect.from_dict(data.get("expect", {})),
        )
