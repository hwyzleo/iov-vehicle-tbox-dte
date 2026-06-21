"""Session record model for DTE."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class StepResult:
    """Result of executing a single test step."""

    step_id: str
    verdict: str
    request_bytes: bytes
    response_bytes: bytes
    parsed: dict[str, Any] | None = None
    timestamp: str | None = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float | None = None
    nrc: int | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "verdict": self.verdict,
            "request_bytes": self.request_bytes.hex(),
            "response_bytes": self.response_bytes.hex(),
            "parsed": self.parsed,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "nrc": self.nrc,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepResult:
        """Create from dictionary."""
        return cls(
            step_id=data["step_id"],
            verdict=data["verdict"],
            request_bytes=bytes.fromhex(data["request_bytes"]),
            response_bytes=bytes.fromhex(data["response_bytes"]),
            parsed=data.get("parsed"),
            timestamp=data.get("timestamp"),
            duration_ms=data.get("duration_ms"),
            nrc=data.get("nrc"),
            error_message=data.get("error_message"),
        )


@dataclass
class SessionRecord:
    """Record of a diagnostic session execution."""

    session_id: str
    transport: str = "doip"
    profile: str | None = None
    state: str = "running"
    step_results: list[StepResult] = field(default_factory=list)
    frames: list[dict[str, Any]] = field(default_factory=list)
    started_at: str | None = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None

    @property
    def passed(self) -> bool:
        """Check if all steps passed."""
        if not self.step_results:
            return False
        return all(r.verdict == "pass" for r in self.step_results)

    def add_step_result(self, result: StepResult) -> None:
        """Add a step result to the session."""
        self.step_results.append(result)

    def add_frame(self, frame: dict[str, Any]) -> None:
        """Add a protocol frame to the session."""
        self.frames.append(frame)

    def finalize(self) -> None:
        """Mark the session as complete."""
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.state = "completed"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "transport": self.transport,
            "profile": self.profile,
            "state": self.state,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "step_results": [r.to_dict() for r in self.step_results],
            "frames": self.frames,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRecord:
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            transport=data.get("transport", "doip"),
            profile=data.get("profile"),
            state=data.get("state", "running"),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            step_results=[StepResult.from_dict(r) for r in data.get("step_results", [])],
            frames=data.get("frames", []),
        )
