"""Session record model for DTE."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class StepResult:
    """Result of executing a single test step."""

    step_name: str
    passed: bool
    request_data: bytes
    response_data: bytes
    nrc: int | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_name": self.step_name,
            "passed": self.passed,
            "request_data": self.request_data.hex(),
            "response_data": self.response_data.hex(),
            "nrc": self.nrc,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepResult:
        """Create from dictionary."""
        return cls(
            step_name=data["step_name"],
            passed=data["passed"],
            request_data=bytes.fromhex(data["request_data"]),
            response_data=bytes.fromhex(data["response_data"]),
            nrc=data.get("nrc"),
            error_message=data.get("error_message"),
        )


@dataclass
class SessionRecord:
    """Record of a diagnostic session execution."""

    session_id: str
    transport_type: str = "doip"
    results: list[StepResult] = field(default_factory=list)
    start_time: str | None = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: str | None = None

    @property
    def passed(self) -> bool:
        """Check if all steps passed."""
        if not self.results:
            return False
        return all(r.passed for r in self.results)

    def add_result(self, result: StepResult) -> None:
        """Add a step result to the session."""
        self.results.append(result)

    def finalize(self) -> None:
        """Mark the session as complete."""
        self.end_time = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "transport_type": self.transport_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRecord:
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            transport_type=data.get("transport_type", "doip"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            results=[StepResult.from_dict(r) for r in data.get("results", [])],
        )
