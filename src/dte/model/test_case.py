"""Test case model for DTE."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dte.model.test_step import TestStep


@dataclass
class TestCase:
    """A test case containing multiple test steps."""

    id: str
    name: str
    steps: list[TestStep] = field(default_factory=list)
    profile_ref: str | None = None
    on_failure: str = "abort"

    def validate(self) -> list[str]:
        """Validate the test case.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors: list[str] = []
        if not self.id:
            errors.append("Test case id is required")
        if not self.name:
            errors.append("Test case name is required")
        if len(self.steps) == 0:
            errors.append("Test case must have at least one step")
        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "profile_ref": self.profile_ref,
            "on_failure": self.on_failure,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            profile_ref=data.get("profile_ref"),
            on_failure=data.get("on_failure", "abort"),
            steps=[TestStep.from_dict(s) for s in data.get("steps", [])],
        )
