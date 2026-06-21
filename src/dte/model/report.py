"""Report model for DTE."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dte.model.session import SessionRecord


@dataclass
class ReportSummary:
    """Summary statistics for a test report."""

    total: int
    passed: int
    failed: int
    errors: int = 0
    skipped: int = 0
    duration_ms: float | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100.0


@dataclass
class Report:
    """Test execution report."""

    session_id: str
    exit_code: int = 0
    session_records: list[SessionRecord] = field(default_factory=list)

    @classmethod
    def from_session_records(
        cls,
        session_id: str,
        exit_code: int = 0,
        records: list[SessionRecord] | None = None,
    ) -> Report:
        """Create a report from session records."""
        return cls(
            session_id=session_id,
            exit_code=exit_code,
            session_records=records or [],
        )

    @property
    def summary(self) -> ReportSummary:
        """Calculate report summary from session records."""
        total = 0
        passed = 0
        failed = 0
        for record in self.session_records:
            for r in record.results:
                total += 1
                if r.verdict == "pass":
                    passed += 1
                else:
                    failed += 1
        return ReportSummary(total=total, passed=passed, failed=failed)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "exit_code": self.exit_code,
            "session_records": [r.to_dict() for r in self.session_records],
            "summary": {
                "total": self.summary.total,
                "passed": self.summary.passed,
                "failed": self.summary.failed,
                "errors": self.summary.errors,
                "skipped": self.summary.skipped,
                "duration_ms": self.summary.duration_ms,
                "success_rate": self.summary.success_rate,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Report:
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            exit_code=data.get("exit_code", 0),
            session_records=[
                SessionRecord.from_dict(r) for r in data.get("session_records", [])
            ],
        )
