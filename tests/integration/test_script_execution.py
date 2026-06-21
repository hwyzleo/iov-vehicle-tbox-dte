"""Integration tests for script execution."""
from __future__ import annotations

from unittest.mock import MagicMock

from dte.engine.executor import ScriptExecutor
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep
from dte.uds.client import UDSClient, UDSResponse


def _make_positive_response(service_id: int = 0x62) -> UDSResponse:
    """Create a positive UDS response."""
    return UDSResponse(
        service_id=service_id,
        positive=True,
        data=b"",
        raw=bytes([service_id]),
    )


def _make_negative_response(service_id: int = 0x22, nrc: int = 0x31) -> UDSResponse:
    """Create a negative UDS response."""
    return UDSResponse(
        service_id=0x7F,
        positive=False,
        data=bytes([service_id, nrc]),
        raw=bytes([0x7F, service_id, nrc]),
        nrc=nrc,
    )


class TestScriptExecutorIntegration:
    """Integration tests for script executor with various scenarios."""

    def test_execute_single_read_did(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = _make_positive_response(0x62)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-001",
            name="Read VIN",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x22, did=0xF190),
                    expect=StepExpect(success=True, sid=0x62),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 1
        assert record.step_results[0].verdict == "pass"
        assert record.passed is True
        assert record.state == "completed"

    def test_execute_multiple_services(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.session_control.return_value = _make_positive_response(0x50)
        mock_client.read_did.return_value = _make_positive_response(0x62)
        mock_client.write_did.return_value = _make_positive_response(0x6E)
        mock_client.routine_control.return_value = _make_positive_response(0x71)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-002",
            name="Multi-service test",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x10, sub_function=0x03),
                    expect=StepExpect(success=True, sid=0x50),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x22, did=0xF190),
                    expect=StepExpect(success=True, sid=0x62),
                ),
                TestStep(
                    id="S3",
                    request=StepRequest(service=0x2E, did=0xF190, data=b"VIN123"),
                    expect=StepExpect(success=True, sid=0x6E),
                ),
                TestStep(
                    id="S4",
                    request=StepRequest(service=0x31, routine_id=0xFF00, control_type=0x01),
                    expect=StepExpect(success=True, sid=0x71),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 4
        assert all(r.verdict == "pass" for r in record.step_results)
        assert record.passed is True

    def test_execute_with_failure_continue(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.side_effect = [
            _make_positive_response(0x62),
            _make_negative_response(0x22, 0x31),
            _make_positive_response(0x62),
        ]

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-003",
            name="Continue on failure",
            on_failure="continue",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x22, did=0xF190),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x22, did=0xF191),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S3",
                    request=StepRequest(service=0x22, did=0xF192),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 3
        assert record.step_results[0].verdict == "pass"
        assert record.step_results[1].verdict == "fail"
        assert record.step_results[2].verdict == "pass"
        assert record.state == "completed"

    def test_execute_with_failure_abort(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.side_effect = [
            _make_positive_response(0x62),
            _make_negative_response(0x22, 0x31),
            _make_positive_response(0x62),
        ]

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-004",
            name="Abort on failure",
            on_failure="abort",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x22, did=0xF190),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x22, did=0xF191),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S3",
                    request=StepRequest(service=0x22, did=0xF192),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 2
        assert record.step_results[0].verdict == "pass"
        assert record.step_results[1].verdict == "fail"
        assert record.state == "aborted"

    def test_execute_with_exception(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.side_effect = Exception("Transport error")

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-005",
            name="Exception handling",
            on_failure="continue",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x22, did=0xF190),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 1
        assert record.step_results[0].verdict == "error"
        assert "Transport error" in record.step_results[0].error_message

    def test_execute_dtc_operations(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_dtc.return_value = UDSResponse(
            service_id=0x59,
            positive=True,
            data=b"\x00\x00",
            raw=b"\x59\x00\x00",
        )
        mock_client.clear_dtc.return_value = _make_positive_response(0x54)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-006",
            name="DTC operations",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x19, data=b"\xFF"),
                    expect=StepExpect(success=True, sid=0x59),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x14, data=b"\xFF\xFF\xFF"),
                    expect=StepExpect(success=True, sid=0x54),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 2
        assert all(r.verdict == "pass" for r in record.step_results)

    def test_execute_security_access(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.security_access.return_value = _make_positive_response(0x67)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-007",
            name="Security access",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x27, sub_function=0x01),
                    expect=StepExpect(success=True, sid=0x67),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 1
        assert record.step_results[0].verdict == "pass"

    def test_execute_io_control(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.io_control.return_value = _make_positive_response(0x6F)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-008",
            name="IO control",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x2F, did=0x0100, control_type=0x03),
                    expect=StepExpect(success=True, sid=0x6F),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 1
        assert record.step_results[0].verdict == "pass"

    def test_execute_unsupported_service(self):
        mock_client = MagicMock(spec=UDSClient)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-009",
            name="Unsupported service",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0xFF),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 1
        assert record.step_results[0].verdict == "error"
        assert "Unsupported service" in record.step_results[0].error_message

    def test_execute_empty_test_case(self):
        mock_client = MagicMock(spec=UDSClient)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC-010",
            name="Empty test case",
            steps=[],
        )

        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 0
        assert record.passed is False
        assert record.state == "completed"
