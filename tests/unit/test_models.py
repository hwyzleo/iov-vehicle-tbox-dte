"""Tests for DTE data models."""
from __future__ import annotations

from dte.model.report import Report, ReportSummary
from dte.model.session import SessionRecord, StepResult
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep


class TestStepRequest:
    """Tests for StepRequest dataclass."""

    def test_default_values(self):
        req = StepRequest(service=0x10, data=b"\x01")
        assert req.service == 0x10
        assert req.data == b"\x01"
        assert req.did is None
        assert req.routine_id is None
        assert req.control_type is None
        assert req.sub_function is None

    def test_custom_values(self):
        req = StepRequest(
            service=0x22, data=b"\xF1\x90", routine_id=0x1234, control_type=0x01, sub_function=0x01
        )
        assert req.service == 0x22
        assert req.data == b"\xF1\x90"
        assert req.did is None
        assert req.routine_id == 0x1234
        assert req.control_type == 0x01
        assert req.sub_function == 0x01

    def test_to_dict(self):
        req = StepRequest(service=0x22, data=b"\xF1\x90", routine_id=0x1234)
        result = req.to_dict()
        assert result["service"] == 0x22
        assert result["data"] == "f190"
        assert result["did"] is None
        assert result["routine_id"] == 0x1234
        assert result["control_type"] is None
        assert result["sub_function"] is None

    def test_from_dict(self):
        data = {"service": 0x22, "data": "f190", "routine_id": 0x1234}
        req = StepRequest.from_dict(data)
        assert req.service == 0x22
        assert req.data == b"\xf1\x90"
        assert req.routine_id == 0x1234

    def test_from_dict_minimal(self):
        data = {"service": 0x10, "data": "01"}
        req = StepRequest.from_dict(data)
        assert req.service == 0x10
        assert req.data == b"\x01"
        assert req.routine_id is None


class TestStepExpect:
    """Tests for StepExpect dataclass."""

    def test_default_values(self):
        expect = StepExpect()
        assert expect.sid is None
        assert expect.success is True
        assert expect.nrc is None
        assert expect.did_data_match is None

    def test_success_response(self):
        expect = StepExpect(success=True, did_data_match=True)
        assert expect.success is True
        assert expect.did_data_match is True

    def test_failure_response(self):
        expect = StepExpect(success=False, nrc=0x12)
        assert expect.success is False
        assert expect.nrc == 0x12

    def test_to_dict(self):
        expect = StepExpect(success=True, did_data_match=True)
        result = expect.to_dict()
        assert result["sid"] is None
        assert result["success"] is True
        assert result["nrc"] is None
        assert result["did_data_match"] is True

    def test_from_dict(self):
        data = {"success": True, "did_data_match": True}
        expect = StepExpect.from_dict(data)
        assert expect.success is True
        assert expect.did_data_match is True

    def test_from_dict_failure(self):
        data = {"success": False, "nrc": 0x12}
        expect = StepExpect.from_dict(data)
        assert expect.success is False
        assert expect.nrc == 0x12


class TestTestStep:
    """Tests for TestStep dataclass."""

    def test_create_step(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        assert step.id == "step_01"
        assert step.request == req
        assert step.expect == expect
        assert step.description is None

    def test_with_description(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect, description="Switch to session")
        assert step.description == "Switch to session"

    def test_to_dict(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        result = step.to_dict()
        assert result["id"] == "step_01"
        assert result["description"] is None
        assert result["request"]["service"] == 0x10
        assert result["expect"]["success"] is True

    def test_from_dict(self):
        data = {
            "id": "step_01",
            "description": "Switch session",
            "request": {"service": 0x10, "data": "01"},
            "expect": {"success": True},
        }
        step = TestStep.from_dict(data)
        assert step.id == "step_01"
        assert step.description == "Switch session"
        assert step.request.service == 0x10
        assert step.expect.success is True

    def test_from_dict_minimal(self):
        data = {
            "id": "step_01",
            "request": {"service": 0x10, "data": "01"},
            "expect": {},
        }
        step = TestStep.from_dict(data)
        assert step.id == "step_01"
        assert step.description is None


class TestCaseModel:
    """Tests for TestCase dataclass."""

    def test_create_test_case(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        tc = TestCase(id="tc_01", name="test_session", steps=[step])
        assert tc.id == "tc_01"
        assert tc.name == "test_session"
        assert len(tc.steps) == 1
        assert tc.profile_ref is None
        assert tc.on_failure == "abort"

    def test_with_profile_ref(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        tc = TestCase(id="tc_01", name="test_session", steps=[step], profile_ref="doip_profile")
        assert tc.profile_ref == "doip_profile"

    def test_on_failure_continue(self):
        tc = TestCase(id="tc_01", name="test", steps=[], on_failure="continue")
        assert tc.on_failure == "continue"

    def test_validate_empty_id(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        tc = TestCase(id="", name="test", steps=[step])
        errors = tc.validate()
        assert any("id" in e for e in errors)

    def test_validate_empty_name(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        tc = TestCase(id="tc_01", name="", steps=[step])
        errors = tc.validate()
        assert any("name" in e for e in errors)

    def test_validate_no_steps(self):
        tc = TestCase(id="tc_01", name="test", steps=[])
        errors = tc.validate()
        assert any("step" in e for e in errors)

    def test_validate_valid(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        tc = TestCase(id="tc_01", name="test", steps=[step])
        assert tc.validate() == []

    def test_to_dict(self):
        req = StepRequest(service=0x10, data=b"\x01")
        expect = StepExpect(success=True)
        step = TestStep(id="step_01", request=req, expect=expect)
        tc = TestCase(id="tc_01", name="test_session", steps=[step], profile_ref="doip")
        result = tc.to_dict()
        assert result["id"] == "tc_01"
        assert result["name"] == "test_session"
        assert result["profile_ref"] == "doip"
        assert result["on_failure"] == "abort"
        assert len(result["steps"]) == 1

    def test_from_dict(self):
        data = {
            "id": "tc_01",
            "name": "test_session",
            "profile_ref": "doip",
            "on_failure": "continue",
            "steps": [
                {
                    "id": "step_01",
                    "request": {"service": 0x10, "data": "01"},
                    "expect": {"success": True},
                }
            ],
        }
        tc = TestCase.from_dict(data)
        assert tc.id == "tc_01"
        assert tc.name == "test_session"
        assert tc.profile_ref == "doip"
        assert tc.on_failure == "continue"
        assert len(tc.steps) == 1
        assert tc.steps[0].id == "step_01"


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_passed_result(self):
        result = StepResult(
            step_id="step_01",
            verdict="pass",
            request_bytes=b"\x10\x01",
            response_bytes=b"\x50\x01",
        )
        assert result.step_id == "step_01"
        assert result.verdict == "pass"
        assert result.request_bytes == b"\x10\x01"
        assert result.response_bytes == b"\x50\x01"
        assert result.parsed is None
        assert result.timestamp is not None
        assert result.duration_ms is None
        assert result.error_message is None
        assert result.nrc is None

    def test_failed_result(self):
        result = StepResult(
            step_id="step_02",
            verdict="fail",
            request_bytes=b"\x22\xf1\x90",
            response_bytes=b"\x7f\x22\x12",
            nrc=0x12,
            error_message="SubFunctionNotSupported",
            duration_ms=150.5,
        )
        assert result.verdict == "fail"
        assert result.nrc == 0x12
        assert result.error_message == "SubFunctionNotSupported"
        assert result.duration_ms == 150.5

    def test_to_dict(self):
        result = StepResult(
            step_id="step_01",
            verdict="pass",
            request_bytes=b"\x10\x01",
            response_bytes=b"\x50\x01",
            parsed={"service": "DiagnosticSessionControl"},
            duration_ms=50.0,
        )
        d = result.to_dict()
        assert d["step_id"] == "step_01"
        assert d["verdict"] == "pass"
        assert d["request_bytes"] == "1001"
        assert d["response_bytes"] == "5001"
        assert d["parsed"] == {"service": "DiagnosticSessionControl"}
        assert d["duration_ms"] == 50.0
        assert d["nrc"] is None

    def test_from_dict(self):
        d = {
            "step_id": "step_01",
            "verdict": "pass",
            "request_bytes": "1001",
            "response_bytes": "5001",
            "parsed": {"service": "DiagnosticSessionControl"},
            "timestamp": "2026-06-21T10:00:00",
            "duration_ms": 50.0,
        }
        result = StepResult.from_dict(d)
        assert result.step_id == "step_01"
        assert result.verdict == "pass"
        assert result.request_bytes == b"\x10\x01"
        assert result.response_bytes == b"\x50\x01"
        assert result.parsed == {"service": "DiagnosticSessionControl"}
        assert result.duration_ms == 50.0


class TestSessionRecord:
    """Tests for SessionRecord dataclass."""

    def test_create_session(self):
        session = SessionRecord(session_id="sess-001")
        assert session.session_id == "sess-001"
        assert session.transport == "doip"
        assert session.profile is None
        assert session.state == "running"
        assert session.step_results == []
        assert session.frames == []
        assert session.started_at is not None
        assert session.ended_at is None

    def test_add_step_result(self):
        session = SessionRecord(session_id="sess-001")
        result = StepResult(
            step_id="step_01",
            verdict="pass",
            request_bytes=b"\x10\x01",
            response_bytes=b"\x50\x01",
        )
        session.add_step_result(result)
        assert len(session.step_results) == 1
        assert session.step_results[0] == result

    def test_add_frame(self):
        session = SessionRecord(session_id="sess-001")
        frame = {"direction": "tx", "data": "1001"}
        session.add_frame(frame)
        assert len(session.frames) == 1
        assert session.frames[0] == frame

    def test_passed_all(self):
        session = SessionRecord(session_id="sess-001")
        session.add_step_result(
            StepResult(step_id="s1", verdict="pass", request_bytes=b"", response_bytes=b"")
        )
        session.add_step_result(
            StepResult(step_id="s2", verdict="pass", request_bytes=b"", response_bytes=b"")
        )
        assert session.passed is True

    def test_passed_with_failure(self):
        session = SessionRecord(session_id="sess-001")
        session.add_step_result(
            StepResult(step_id="s1", verdict="pass", request_bytes=b"", response_bytes=b"")
        )
        session.add_step_result(
            StepResult(step_id="s2", verdict="fail", request_bytes=b"", response_bytes=b"")
        )
        assert session.passed is False

    def test_passed_empty(self):
        session = SessionRecord(session_id="sess-001")
        assert session.passed is False

    def test_finalize(self):
        session = SessionRecord(session_id="sess-001")
        assert session.ended_at is None
        assert session.state == "running"
        session.finalize()
        assert session.ended_at is not None
        assert session.state == "completed"

    def test_to_dict(self):
        session = SessionRecord(session_id="sess-001", transport="can", profile="can_profile")
        session.add_step_result(
            StepResult(
                step_id="step_01", verdict="pass", request_bytes=b"\x10", response_bytes=b"\x50"
            )
        )
        d = session.to_dict()
        assert d["session_id"] == "sess-001"
        assert d["transport"] == "can"
        assert d["profile"] == "can_profile"
        assert d["state"] == "running"
        assert len(d["step_results"]) == 1
        assert d["frames"] == []

    def test_from_dict(self):
        d = {
            "session_id": "sess-001",
            "transport": "doip",
            "profile": "doip_profile",
            "state": "completed",
            "started_at": "2026-06-21T10:00:00",
            "ended_at": "2026-06-21T10:00:01",
            "step_results": [
                {
                    "step_id": "step_01",
                    "verdict": "pass",
                    "request_bytes": "10",
                    "response_bytes": "50",
                }
            ],
            "frames": [{"direction": "tx", "data": "10"}],
        }
        session = SessionRecord.from_dict(d)
        assert session.session_id == "sess-001"
        assert session.transport == "doip"
        assert session.profile == "doip_profile"
        assert session.state == "completed"
        assert len(session.step_results) == 1
        assert len(session.frames) == 1


class TestReportSummary:
    """Tests for ReportSummary dataclass."""

    def test_summary(self):
        summary = ReportSummary(total=10, passed=8, failed=2)
        assert summary.total == 10
        assert summary.passed == 8
        assert summary.failed == 2
        assert summary.errors == 0
        assert summary.skipped == 0
        assert summary.duration_ms is None

    def test_success_rate(self):
        summary = ReportSummary(total=10, passed=8, failed=2)
        assert summary.success_rate == 80.0

    def test_success_rate_all_passed(self):
        summary = ReportSummary(total=5, passed=5, failed=0)
        assert summary.success_rate == 100.0

    def test_success_rate_zero_total(self):
        summary = ReportSummary(total=0, passed=0, failed=0)
        assert summary.success_rate == 0.0

    def test_with_errors_and_skipped(self):
        summary = ReportSummary(
            total=10, passed=6, failed=2, errors=1, skipped=1, duration_ms=5000.0
        )
        assert summary.errors == 1
        assert summary.skipped == 1
        assert summary.duration_ms == 5000.0


class TestReport:
    """Tests for Report dataclass."""

    def test_create_report(self):
        session = SessionRecord(session_id="sess-001")
        session.add_step_result(
            StepResult(
                step_id="step_01", verdict="pass", request_bytes=b"\x10", response_bytes=b"\x50"
            )
        )
        session.finalize()
        report = Report(session_id="sess-001", session_records=[session])
        assert report.session_id == "sess-001"
        assert report.exit_code == 0
        assert len(report.session_records) == 1
        assert report.summary.total == 1
        assert report.summary.passed == 1
        assert report.summary.failed == 0

    def test_report_with_failures(self):
        session = SessionRecord(session_id="sess-001")
        session.add_step_result(
            StepResult(
                step_id="s1", verdict="pass", request_bytes=b"\x10", response_bytes=b"\x50"
            )
        )
        session.add_step_result(
            StepResult(
                step_id="s2", verdict="fail", request_bytes=b"\x22", response_bytes=b"\x7f"
            )
        )
        session.finalize()
        report = Report(session_id="sess-001", session_records=[session])
        assert report.summary.total == 2
        assert report.summary.passed == 1
        assert report.summary.failed == 1

    def test_from_session_records(self):
        session = SessionRecord(session_id="sess-001")
        session.add_step_result(
            StepResult(
                step_id="step_01", verdict="pass", request_bytes=b"\x10", response_bytes=b"\x50"
            )
        )
        report = Report.from_session_records(session_id="sess-001", exit_code=0, records=[session])
        assert report.session_id == "sess-001"
        assert report.exit_code == 0
        assert len(report.session_records) == 1

    def test_to_dict(self):
        session = SessionRecord(session_id="sess-001")
        session.add_step_result(
            StepResult(
                step_id="step_01", verdict="pass", request_bytes=b"\x10", response_bytes=b"\x50"
            )
        )
        session.finalize()
        report = Report(session_id="sess-001", exit_code=0, session_records=[session])
        d = report.to_dict()
        assert d["session_id"] == "sess-001"
        assert d["exit_code"] == 0
        assert d["summary"]["total"] == 1
        assert "session_records" in d

    def test_from_dict(self):
        d = {
            "session_id": "sess-001",
            "exit_code": 0,
            "session_records": [
                {
                    "session_id": "sess-001",
                    "transport": "doip",
                    "state": "completed",
                    "started_at": "2026-06-21T10:00:00",
                    "ended_at": "2026-06-21T10:00:01",
                    "step_results": [
                        {
                            "step_id": "step_01",
                            "verdict": "pass",
                            "request_bytes": "10",
                            "response_bytes": "50",
                        }
                    ],
                }
            ],
        }
        report = Report.from_dict(d)
        assert report.session_id == "sess-001"
        assert report.exit_code == 0
        assert len(report.session_records) == 1
        assert report.summary.total == 1
