"""Tests for script executor."""
from __future__ import annotations

from unittest.mock import MagicMock

from dte.engine.assertion import AssertionEngine
from dte.engine.executor import ScriptExecutor
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep
from dte.uds.client import UDSClient, UDSResponse


def _make_test_step(step_id: str = "S1", service: int = 0x22) -> TestStep:
    """Create a minimal test step."""
    return TestStep(
        id=step_id,
        request=StepRequest(service=service),
        expect=StepExpect(success=True),
    )


def _make_positive_response(service_id: int = 0x62) -> UDSResponse:
    """Create a positive UDS response."""
    return UDSResponse(
        service_id=service_id,
        positive=True,
        data=b"",
        raw=bytes([service_id]),
    )


def _make_negative_response(nrc: int = 0x31) -> UDSResponse:
    """Create a negative UDS response."""
    return UDSResponse(
        service_id=0x7F,
        positive=False,
        data=bytes([0x22, nrc]),
        raw=bytes([0x7F, 0x22, nrc]),
        nrc=nrc,
    )


class TestScriptExecutorInit:
    """Tests for ScriptExecutor initialization."""

    def test_init_with_defaults(self):
        executor = ScriptExecutor()
        assert executor._assertion_engine is not None

    def test_init_with_custom_engine(self):
        engine = AssertionEngine()
        executor = ScriptExecutor(assertion_engine=engine)
        assert executor._assertion_engine is engine


class TestScriptExecutorRunStep:
    """Tests for ScriptExecutor.run_step."""

    def test_run_step_pass(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = _make_positive_response()

        executor = ScriptExecutor()
        step = TestStep(
            id="S1",
            request=StepRequest(service=0x22, did=0xF190),
            expect=StepExpect(success=True),
        )
        result = executor.run_step(mock_client, step)

        assert result.step_id == "S1"
        assert result.verdict == "pass"
        mock_client.read_did.assert_called_once_with(0xF190)

    def test_run_step_fail(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = _make_negative_response(nrc=0x31)

        executor = ScriptExecutor()
        step = TestStep(
            id="S1",
            request=StepRequest(service=0x22, did=0xF190),
            expect=StepExpect(success=True),
        )
        result = executor.run_step(mock_client, step)

        assert result.step_id == "S1"
        assert result.verdict == "fail"

    def test_run_step_session_control(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.session_control.return_value = _make_positive_response(0x50)

        executor = ScriptExecutor()
        step = TestStep(
            id="S1",
            request=StepRequest(service=0x10),
            expect=StepExpect(success=True),
        )
        result = executor.run_step(mock_client, step)

        assert result.verdict == "pass"
        mock_client.session_control.assert_called_once()

    def test_run_step_write_did(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.write_did.return_value = _make_positive_response(0x6E)

        executor = ScriptExecutor()
        step = TestStep(
            id="S1",
            request=StepRequest(service=0x2E, did=0xF190, data=b"VIN"),
            expect=StepExpect(success=True),
        )
        result = executor.run_step(mock_client, step)

        assert result.verdict == "pass"
        mock_client.write_did.assert_called_once_with(0xF190, b"VIN")

    def test_run_step_routine_control(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.routine_control.return_value = _make_positive_response(0x71)

        executor = ScriptExecutor()
        step = TestStep(
            id="S1",
            request=StepRequest(service=0x31, routine_id=0xFF00, control_type=0x01),
            expect=StepExpect(success=True),
        )
        result = executor.run_step(mock_client, step)

        assert result.verdict == "pass"
        mock_client.routine_control.assert_called_once_with(0xFF00, 0x01, data=None)

    def test_run_step_exception_captured(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.side_effect = Exception("Connection lost")

        executor = ScriptExecutor()
        step = TestStep(
            id="S1",
            request=StepRequest(service=0x22, did=0xF190),
            expect=StepExpect(success=True),
        )
        result = executor.run_step(mock_client, step)

        assert result.step_id == "S1"
        assert result.verdict == "error"
        assert "Connection lost" in result.error_message


class TestScriptExecutorRunTestCase:
    """Tests for ScriptExecutor.run_test_case."""

    def test_run_test_case_all_pass(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = _make_positive_response(0x62)

        executor = ScriptExecutor()
        case = TestCase(
            id="TC1",
            name="Read VIN",
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
            ],
        )
        record = executor.run_test_case(mock_client, case)

        assert len(record.step_results) == 2
        assert record.step_results[0].verdict == "pass"
        assert record.step_results[1].verdict == "pass"
        assert record.passed is True

    def test_run_test_case_abort_on_failure(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.side_effect = [
            _make_positive_response(0x62),
            _make_negative_response(0x31),
        ]

        executor = ScriptExecutor()
        case = TestCase(
            id="TC1",
            name="Test",
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

    def test_run_test_case_continue_on_failure(self):
        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.side_effect = [
            _make_positive_response(0x62),
            _make_negative_response(0x31),
            _make_positive_response(0x62),
        ]

        executor = ScriptExecutor()
        case = TestCase(
            id="TC1",
            name="Test",
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
        assert record.step_results[1].verdict == "fail"
        assert record.step_results[2].verdict == "pass"
        assert record.state == "completed"
