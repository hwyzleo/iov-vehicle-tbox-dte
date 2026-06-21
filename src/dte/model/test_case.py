"""Test case model for DTE."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dte.model.test_step import TestStep


@dataclass
class TestCase:
    """A test case containing multiple test steps."""

    name: str
    steps: list[TestStep] = field(default_factory=list)
    description: str | None = None

    def validate(self) -> list[str]:
        """Validate the test case.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors: list[str] = []
        if not self.name:
            errors.append("Test case name is required")
        if len(self.steps) == 0:
            errors.append("Test case must have at least one step")
        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description"),
            steps=[TestStep.from_dict(s) for s in data.get("steps", [])],
        )
