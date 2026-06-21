"""Integration tests for Aftersales scenario execution."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dte.engine.scenario import ScenarioEngine
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep
from dte.transport.base import BaseTransport
from dte.uds.client import UDSResponse


def _make_aftersales_test_case() -> TestCase:
    """Create a representative aftersales test case with DTC operations."""
    return TestCase(
        id="AFTR-DTC-001",
        name="Aftersales DTC Diagnostic",
        on_failure="continue",
        steps=[
            TestStep(
                id="AFTR-S01",
                description="Switch to default session",
                request=StepRequest(service=0x10, sub_function=0x01),
                expect=StepExpect(success=True, sid=0x50),
            ),
            TestStep(
                id="AFTR-S02",
                description="Read DTCs by status mask",
                request=StepRequest(service=0x19, data=b"\xFF"),
                expect=StepExpect(success=True, sid=0x59),
            ),
            TestStep(
                id="AFTR-S03",
                description="Switch to extended session",
                request=StepRequest(service=0x10, sub_function=0x03),
                expect=StepExpect(success=True, sid=0x50),
            ),
            TestStep(
                id="AFTR-S04",
                description="Clear all DTCs",
                request=StepRequest(service=0x14, data=b"\xFF\xFF\xFF"),
                expect=StepExpect(success=True, sid=0x54),
            ),
        ],
    )


class TestAftersalesScenarioIntegration:
    """Integration tests for end-to-end aftersales scenario execution."""

    def test_aftersales_all_steps_pass(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock()

        def mock_session_control(session_type):
            return UDSResponse(
                service_id=0x50, positive=True, data=b"\x01", raw=b"\x50\x01"
            )

        def mock_read_dtc(status_mask):
            return UDSResponse(
                service_id=0x59, positive=True, data=b"\x00", raw=b"\x59\x00"
            )

        def mock_clear_dtc(group=0xFFFFFF):
            return UDSResponse(
                service_id=0x54, positive=True, data=b"", raw=b"\x54"
            )

        mock_client.session_control = mock_session_control
        mock_client.read_dtc = mock_read_dtc
        mock_client.clear_dtc = mock_clear_dtc

        engine = ScenarioEngine()
        with pytest.MonkeyPatch.context() as m:
            m.setattr(engine, "_create_client", lambda transport: mock_client)
            report = engine.run(mock_transport, [_make_aftersales_test_case()])

        assert report.exit_code == 0
        assert len(report.session_records) == 1
        record = report.session_records[0]
        assert len(record.step_results) == 4
        assert all(r.verdict == "pass" for r in record.step_results)
        assert record.passed is True

    def test_aftersales_partial_failure_continue(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock()

        def mock_session_control(session_type):
            return UDSResponse(
                service_id=0x50, positive=True, data=b"\x01", raw=b"\x50\x01"
            )

        call_count = 0

        def mock_read_dtc(status_mask):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return UDSResponse(
                    service_id=0x7F,
                    positive=False,
                    data=bytes([0x19, 0x31]),
                    raw=bytes([0x7F, 0x19, 0x31]),
                    nrc=0x31,
                )
            return UDSResponse(
                service_id=0x59, positive=True, data=b"\x00", raw=b"\x59\x00"
            )

        def mock_clear_dtc(group=0xFFFFFF):
            return UDSResponse(
                service_id=0x54, positive=True, data=b"", raw=b"\x54"
            )

        mock_client.session_control = mock_session_control
        mock_client.read_dtc = mock_read_dtc
        mock_client.clear_dtc = mock_clear_dtc

        engine = ScenarioEngine()
        with pytest.MonkeyPatch.context() as m:
            m.setattr(engine, "_create_client", lambda transport: mock_client)
            report = engine.run(mock_transport, [_make_aftersales_test_case()])

        assert report.exit_code == 1
        record = report.session_records[0]
        assert record.step_results[0].verdict == "pass"
        assert record.step_results[1].verdict == "fail"
        assert record.step_results[2].verdict == "pass"
        assert record.step_results[3].verdict == "pass"
        assert record.state == "completed"

    def test_aftersales_abort_on_failure(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock()
        mock_client.session_control.return_value = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x10\x22",
            raw=b"\x7F\x10\x22",
            nrc=0x22,
        )

        abort_case = TestCase(
            id="AFTR-ABORT",
            name="Aftersales Abort Test",
            on_failure="abort",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x10, sub_function=0x01),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x19, data=b"\xFF"),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        engine = ScenarioEngine()
        with pytest.MonkeyPatch.context() as m:
            m.setattr(engine, "_create_client", lambda transport: mock_client)
            report = engine.run(mock_transport, [abort_case])

        record = report.session_records[0]
        assert len(record.step_results) == 1
        assert record.state == "aborted"

    def test_aftersales_multiple_test_cases(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock()

        def mock_session_control(session_type):
            return UDSResponse(
                service_id=0x50, positive=True, data=b"\x01", raw=b"\x50\x01"
            )

        def mock_read_dtc(status_mask):
            return UDSResponse(
                service_id=0x59, positive=True, data=b"\x00", raw=b"\x59\x00"
            )

        def mock_clear_dtc(group=0xFFFFFF):
            return UDSResponse(
                service_id=0x54, positive=True, data=b"", raw=b"\x54"
            )

        mock_client.session_control = mock_session_control
        mock_client.read_dtc = mock_read_dtc
        mock_client.clear_dtc = mock_clear_dtc

        case1 = TestCase(
            id="AFTR-001",
            name="Read DTCs",
            on_failure="continue",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x10, sub_function=0x01),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x19, data=b"\xFF"),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        case2 = TestCase(
            id="AFTR-002",
            name="Clear DTCs",
            on_failure="continue",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x10, sub_function=0x03),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x14, data=b"\xFF\xFF\xFF"),
                    expect=StepExpect(success=True),
                ),
            ],
        )

        engine = ScenarioEngine()
        with pytest.MonkeyPatch.context() as m:
            m.setattr(engine, "_create_client", lambda transport: mock_client)
            report = engine.run(mock_transport, [case1, case2])

        assert report.exit_code == 0
        assert len(report.session_records) == 2
        assert all(r.passed for r in report.session_records)
