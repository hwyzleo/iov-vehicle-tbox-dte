"""Script executor for running test cases step by step."""
from __future__ import annotations

import logging
import time

from dte.config.transport_profile import TransportProfile
from dte.engine.assertion import AssertionEngine
from dte.model.session import SessionRecord, StepResult
from dte.model.test_case import TestCase
from dte.model.test_step import TestStep
from dte.transport.base import BaseTransport
from dte.uds.client import TransportConnection, UDSClient, UDSResponse

logger = logging.getLogger(__name__)


class ScriptExecutor:
    """Executes test cases by running each step against a UDS client."""

    def __init__(self, assertion_engine: AssertionEngine | None = None) -> None:
        self._assertion_engine = assertion_engine or AssertionEngine()

    def _create_client(self, transport: BaseTransport) -> UDSClient:
        """Create a UDSClient connected via the given transport.

        Args:
            transport: Connected transport instance.

        Returns:
            Configured UDSClient.
        """
        conn = TransportConnection(transport)
        return UDSClient(conn=conn)

    def _dispatch(self, client: UDSClient, step: TestStep) -> UDSResponse:
        """Dispatch a test step to the appropriate UDS client method.

        Args:
            client: UDS client to use.
            step: Test step with request details.

        Returns:
            UDSResponse from the client.

        Raises:
            ValueError: If service ID is not supported.
        """
        req = step.request
        service = req.service

        if service == 0x10:
            return client.session_control(req.sub_function or 0x01)
        elif service == 0x22:
            return client.read_did(req.did or 0)
        elif service == 0x2E:
            return client.write_did(req.did or 0, req.data)
        elif service == 0x27:
            return client.security_access(req.sub_function or 0x01)
        elif service == 0x31:
            return client.routine_control(
                req.routine_id or 0,
                req.control_type or 0x01,
                data=req.data if req.data else None,
            )
        elif service == 0x19:
            return client.read_dtc(req.data[0] if req.data else 0xFF)
        elif service == 0x14:
            return client.clear_dtc()
        elif service == 0x2F:
            return client.io_control(req.did or 0, control_type=req.control_type or 0x03)
        else:
            raise ValueError(f"Unsupported service: 0x{service:02X}")

    def run_step(self, client: UDSClient, step: TestStep) -> StepResult:
        """Execute a single test step.

        Args:
            client: UDS client to use for the request.
            step: Test step to execute.

        Returns:
            StepResult with verdict and response data.
        """
        start = time.monotonic()
        try:
            response = self._dispatch(client, step)
            assertion = self._assertion_engine.assert_response(
                response, step.expect, step.request.data
            )
            duration_ms = (time.monotonic() - start) * 1000
            return StepResult(
                step_id=step.id,
                verdict=assertion.verdict,
                request_bytes=step.request.data,
                response_bytes=response.raw,
                duration_ms=duration_ms,
                nrc=response.nrc,
                error_message=assertion.error_message,
            )
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error("Step %s failed with exception: %s", step.id, exc)
            return StepResult(
                step_id=step.id,
                verdict="error",
                request_bytes=step.request.data,
                response_bytes=b"",
                duration_ms=duration_ms,
                error_message=str(exc),
            )

    def execute_test_case(
        self, test_case: TestCase, transport_profile: TransportProfile
    ) -> SessionRecord:
        """Execute all steps in a test case.

        Creates a transport from the profile, connects, runs all steps,
        and disconnects.

        Args:
            test_case: Test case to execute.
            transport_profile: Transport profile to use for creating connection.

        Returns:
            SessionRecord with step results.
        """
        from dte.transport.factory import create_transport

        transport = create_transport(transport_profile)
        transport.connect()
        try:
            client = self._create_client(transport)
            record = SessionRecord(session_id=test_case.id)

            for step in test_case.steps:
                result = self.run_step(client, step)
                record.add_step_result(result)

                if result.verdict == "fail" and test_case.on_failure == "abort":
                    record.finalize()
                    record.state = "aborted"
                    return record

            record.finalize()
            return record
        finally:
            transport.disconnect()

    def run_test_case(self, client: UDSClient, case: TestCase) -> SessionRecord:
        """Execute all steps in a test case with an existing client.

        Args:
            client: UDS client to use for requests.
            case: Test case to execute.

        Returns:
            SessionRecord with step results.
        """
        record = SessionRecord(session_id=case.id)

        for step in case.steps:
            result = self.run_step(client, step)
            record.add_step_result(result)

            if result.verdict == "fail" and case.on_failure == "abort":
                record.finalize()
                record.state = "aborted"
                return record

        record.finalize()
        return record
