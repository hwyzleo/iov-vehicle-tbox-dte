"""Tests for scenario engine."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from dte.config.transport_profile import TransportProfile, TransportType
from dte.engine.executor import ScriptExecutor
from dte.engine.scenario import ScenarioEngine
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep
from dte.transport.base import BaseTransport
from dte.uds.client import UDSClient, UDSResponse


def _make_test_case() -> TestCase:
    """Create a minimal test case."""
    return TestCase(
        id="TC1",
        name="Test Case 1",
        steps=[
            TestStep(
                id="S1",
                request=StepRequest(service=0x22, did=0xF190),
                expect=StepExpect(success=True),
            ),
        ],
    )


def _make_profile() -> TransportProfile:
    """Create a minimal transport profile."""
    return TransportProfile(name="test", transport_type=TransportType.DOIP)


class TestScenarioEngineInit:
    """Tests for ScenarioEngine initialization."""

    def test_init_with_executor(self):
        executor = ScriptExecutor()
        engine = ScenarioEngine(executor=executor)
        assert engine._executor is executor

    def test_init_default_executor(self):
        engine = ScenarioEngine()
        assert isinstance(engine._executor, ScriptExecutor)


class TestScenarioEngineRun:
    """Tests for ScenarioEngine.run."""

    def test_run_single_test_case(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"",
            raw=b"\x62",
        )

        engine = ScenarioEngine()
        with patch.object(engine, "_create_client", return_value=mock_client):
            report = engine.run(mock_transport, [_make_test_case()])

        assert report.exit_code == 0
        assert len(report.session_records) == 1
        assert report.session_records[0].passed is True

    def test_run_multiple_test_cases(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"",
            raw=b"\x62",
        )

        engine = ScenarioEngine()
        with patch.object(engine, "_create_client", return_value=mock_client):
            cases = [_make_test_case(), _make_test_case()]
            report = engine.run(mock_transport, cases)

        assert len(report.session_records) == 2

    def test_run_sets_nonzero_exit_on_failure(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x22\x31",
            raw=b"\x7F\x22\x31",
            nrc=0x31,
        )

        engine = ScenarioEngine()
        with patch.object(engine, "_create_client", return_value=mock_client):
            report = engine.run(mock_transport, [_make_test_case()])

        assert report.exit_code == 1
        assert report.session_records[0].passed is False

    def test_run_connects_transport(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = False

        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"",
            raw=b"\x62",
        )

        engine = ScenarioEngine()
        with patch.object(engine, "_create_client", return_value=mock_client):
            engine.run(mock_transport, [_make_test_case()])

        mock_transport.connect.assert_called_once()

    def test_run_disconnects_on_completion(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock(spec=UDSClient)
        mock_client.read_did.return_value = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"",
            raw=b"\x62",
        )

        engine = ScenarioEngine()
        with patch.object(engine, "_create_client", return_value=mock_client):
            engine.run(mock_transport, [_make_test_case()])

        mock_transport.disconnect.assert_called_once()


class TestScenarioEngineExecuteTestCase:
    """Tests for ScenarioEngine.execute_test_case."""

    def test_execute_test_case_delegates_to_executor(self):
        mock_executor = MagicMock(spec=ScriptExecutor)
        mock_record = MagicMock()
        mock_executor.execute_test_case.return_value = mock_record

        engine = ScenarioEngine(executor=mock_executor)
        profile = _make_profile()
        case = _make_test_case()

        result = engine.execute_test_case(case, profile)

        assert result is mock_record
        mock_executor.execute_test_case.assert_called_once_with(case, profile)


class TestScenarioEngineExecuteTestSuite:
    """Tests for ScenarioEngine.execute_test_suite."""

    def test_execute_test_suite_all_pass(self):
        mock_executor = MagicMock(spec=ScriptExecutor)
        mock_record = MagicMock()
        mock_record.passed = True
        mock_record.step_results = [MagicMock(verdict="pass")]
        mock_executor.execute_test_case.return_value = mock_record

        engine = ScenarioEngine(executor=mock_executor)
        profile = _make_profile()
        cases = [_make_test_case(), _make_test_case()]

        report = engine.execute_test_suite(cases, profile)

        assert report.exit_code == 0
        assert len(report.session_records) == 2
        assert mock_executor.execute_test_case.call_count == 2

    def test_execute_test_suite_with_failure(self):
        mock_executor = MagicMock(spec=ScriptExecutor)
        mock_record = MagicMock()
        mock_record.passed = False
        mock_record.step_results = [MagicMock(verdict="fail")]
        mock_executor.execute_test_case.return_value = mock_record

        engine = ScenarioEngine(executor=mock_executor)
        profile = _make_profile()

        report = engine.execute_test_suite([_make_test_case()], profile)

        assert report.exit_code == 1

    def test_execute_test_suite_empty(self):
        mock_executor = MagicMock(spec=ScriptExecutor)
        engine = ScenarioEngine(executor=mock_executor)
        profile = _make_profile()

        report = engine.execute_test_suite([], profile)

        assert report.exit_code == 0
        assert len(report.session_records) == 0
