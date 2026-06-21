"""Tests for scenario engine."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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
