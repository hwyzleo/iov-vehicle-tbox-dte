"""Report model for DTE."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dte.model.session import SessionRecord


@dataclass
class ReportSummary:
    """Summary statistics for a test report."""

    total: int
    passed: int
    failed: int

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100.0


@dataclass
class Report:
    """Test execution report."""

    test_case_name: str
    session: SessionRecord

    @property
    def summary(self) -> ReportSummary:
        """Calculate report summary from session results."""
        total = len(self.session.results)
        passed = sum(1 for r in self.session.results if r.passed)
        failed = total - passed
        return ReportSummary(total=total, passed=passed, failed=failed)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_case_name": self.test_case_name,
            "session": self.session.to_dict(),
            "summary": {
                "total": self.summary.total,
                "passed": self.summary.passed,
                "failed": self.summary.failed,
                "pass_rate": self.summary.pass_rate,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Report:
        """Create from dictionary."""
        return cls(
            test_case_name=data["test_case_name"],
            session=SessionRecord.from_dict(data["session"]),
        )
