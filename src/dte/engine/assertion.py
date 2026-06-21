"""Assertion engine for validating UDS responses against expectations."""
from __future__ import annotations

from dataclasses import dataclass

from dte.model.test_step import StepExpect
from dte.uds.client import UDSResponse


@dataclass
class AssertionResult:
    """Result of an assertion check.

    Attributes:
        verdict: "pass" or "fail".
        error_message: Description of why assertion failed (None if pass).
    """

    verdict: str
    error_message: str | None = None


class AssertionEngine:
    """Validates UDS responses against expected outcomes."""

    def assert_response(
        self, response: UDSResponse, expect: StepExpect, request_data: bytes = b""
    ) -> AssertionResult:
        """Assert a UDS response matches expectations.

        Args:
            response: The UDS response to validate.
            expect: Expected outcome constraints.
            request_data: Original request data for DID data match comparison.

        Returns:
            AssertionResult with verdict and optional error message.
        """
        errors: list[str] = []

        if expect.success and not response.positive:
            errors.append("Expected positive response but got negative")
        if not expect.success and response.positive:
            errors.append("Expected negative response but got positive")

        if expect.nrc is not None and expect.nrc != response.nrc:
            errors.append(
                f"NRC mismatch: expected 0x{expect.nrc:02X}, got 0x{response.nrc:02X}"
            )

        if expect.sid is not None and expect.sid != response.service_id:
            errors.append(
                f"SID mismatch: expected 0x{expect.sid:02X}, got 0x{response.service_id:02X}"
            )

        if expect.did_data_match is not None:
            if expect.did_data_match and request_data and response.data != request_data:
                errors.append(
                    f"DID data mismatch: expected {request_data.hex()}, "
                    f"got {response.data.hex()}"
                )
            if not expect.did_data_match and request_data and response.data == request_data:
                errors.append("DID data should not match but does")

        if errors:
            return AssertionResult(verdict="fail", error_message="; ".join(errors))
        return AssertionResult(verdict="pass")
