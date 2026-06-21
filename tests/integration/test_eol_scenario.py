"""Integration tests for EOL scenario execution."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dte.engine.scenario import ScenarioEngine
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep
from dte.transport.base import BaseTransport
from dte.uds.client import UDSResponse


def _make_eol_test_case() -> TestCase:
    """Create a representative EOL test case with multiple steps."""
    return TestCase(
        id="EOL-001",
        name="EOL Basic Check",
        on_failure="continue",
        steps=[
            TestStep(
                id="EOL-S1",
                description="Switch to extended session",
                request=StepRequest(service=0x10, sub_function=0x03),
                expect=StepExpect(success=True, sid=0x50),
            ),
            TestStep(
                id="EOL-S2",
                description="Read VIN",
                request=StepRequest(service=0x22, did=0xF190),
                expect=StepExpect(success=True, sid=0x62),
            ),
            TestStep(
                id="EOL-S3",
                description="Read hardware version",
                request=StepRequest(service=0x22, did=0xF191),
                expect=StepExpect(success=True, sid=0x62),
            ),
            TestStep(
                id="EOL-S4",
                description="Write serial number",
                request=StepRequest(service=0x2E, did=0xF192, data=b"SN12345"),
                expect=StepExpect(success=True, sid=0x6E),
            ),
            TestStep(
                id="EOL-S5",
                description="Start EOL routine",
                request=StepRequest(service=0x31, routine_id=0xFF00, control_type=0x01),
                expect=StepExpect(success=True, sid=0x71),
            ),
        ],
    )


class TestEOLScenarioIntegration:
    """Integration tests for end-to-end EOL scenario execution."""

    def test_eol_all_steps_pass(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        responses = {
            0x10: UDSResponse(service_id=0x50, positive=True, data=b"\x03", raw=b"\x50\x03"),
            0xF190: UDSResponse(
                service_id=0x62, positive=True, data=b"\xF1\x90VIN123", raw=b"\x62\xF1\x90VIN123"
            ),
            0xF191: UDSResponse(
                service_id=0x62, positive=True, data=b"\xF1\x91HW1", raw=b"\x62\xF1\x91HW1"
            ),
            0xF192: UDSResponse(
                service_id=0x6E, positive=True, data=b"\xF1\x92", raw=b"\x6E\xF1\x92"
            ),
            0xFF00: UDSResponse(
                service_id=0x71, positive=True, data=b"\xFF\x00", raw=b"\x71\xFF\x00"
            ),
        }

        mock_client = MagicMock()

        def mock_session_control(session_type):
            return responses[0x10]

        def mock_read_did(did):
            return responses[did]

        def mock_write_did(did, data):
            return responses[did]

        def mock_routine_control(routine_id, control_type, data=None):
            return responses[routine_id]

        mock_client.session_control = mock_session_control
        mock_client.read_did = mock_read_did
        mock_client.write_did = mock_write_did
        mock_client.routine_control = mock_routine_control

        engine = ScenarioEngine()
        with pytest.MonkeyPatch.context() as m:
            m.setattr(engine, "_create_client", lambda transport: mock_client)
            report = engine.run(mock_transport, [_make_eol_test_case()])

        assert report.exit_code == 0
        assert len(report.session_records) == 1
        record = report.session_records[0]
        assert len(record.step_results) == 5
        assert all(r.verdict == "pass" for r in record.step_results)
        assert record.passed is True

    def test_eol_partial_failure(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock()

        call_count = 0

        def mock_session_control(session_type):
            return UDSResponse(
                service_id=0x50, positive=True, data=b"\x03", raw=b"\x50\x03"
            )

        def mock_read_did(did):
            nonlocal call_count
            call_count += 1
            if did == 0xF190:
                return UDSResponse(
                    service_id=0x62,
                    positive=True,
                    data=b"\xF1\x90VIN",
                    raw=b"\x62\xF1\x90VIN",
                )
            return UDSResponse(
                service_id=0x7F,
                positive=False,
                data=bytes([0x22, 0x31]),
                raw=bytes([0x7F, 0x22, 0x31]),
                nrc=0x31,
            )

        mock_client.session_control = mock_session_control
        mock_client.read_did = mock_read_did
        mock_client.write_did = lambda did, data: UDSResponse(
            service_id=0x6E, positive=True, data=b"", raw=b"\x6E"
        )
        mock_client.routine_control = lambda rid, ct, data=None: UDSResponse(
            service_id=0x71, positive=True, data=b"", raw=b"\x71"
        )

        engine = ScenarioEngine()
        with pytest.MonkeyPatch.context() as m:
            m.setattr(engine, "_create_client", lambda transport: mock_client)
            report = engine.run(mock_transport, [_make_eol_test_case()])

        assert report.exit_code == 1
        record = report.session_records[0]
        assert record.step_results[0].verdict == "pass"
        assert record.step_results[1].verdict == "pass"
        assert record.step_results[2].verdict == "fail"
        assert record.state == "completed"

    def test_eol_abort_on_failure(self):
        mock_transport = MagicMock(spec=BaseTransport)
        mock_transport.is_connected = True

        mock_client = MagicMock()
        mock_client.session_control.return_value = UDSResponse(
            service_id=0x7F, positive=False, data=b"\x10\x22", raw=b"\x7F\x10\x22", nrc=0x22
        )

        abort_case = TestCase(
            id="EOL-ABORT",
            name="EOL Abort Test",
            on_failure="abort",
            steps=[
                TestStep(
                    id="S1",
                    request=StepRequest(service=0x10, sub_function=0x03),
                    expect=StepExpect(success=True),
                ),
                TestStep(
                    id="S2",
                    request=StepRequest(service=0x22, did=0xF190),
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
