"""Tests for DTE data models."""
from __future__ import annotations

from dte.model.report import Report, ReportSummary
from dte.model.session import SessionRecord, StepResult
from dte.model.test_case import TestCase
from dte.model.test_step import StepExpect, StepRequest, TestStep


class TestStepRequest:
    """Tests for StepRequest dataclass."""

    def test_default_values(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        assert req.sid == 0x10
        assert req.data == b"\x01"
        assert req.did is None
        assert req.sub_function is None

    def test_custom_values(self):
        req = StepRequest(sid=0x22, data=b"\xF1\x90", did=0xF190, sub_function=0x01)
        assert req.sid == 0x22
        assert req.data == b"\xF1\x90"
        assert req.did == 0xF190
        assert req.sub_function == 0x01

    def test_to_dict(self):
        req = StepRequest(sid=0x22, data=b"\xF1\x90", did=0xF190)
        result = req.to_dict()
        assert result["sid"] == 0x22
        assert result["data"] == "f190"
        assert result["did"] == 0xF190
        assert result["sub_function"] is None

    def test_from_dict(self):
        data = {"sid": 0x22, "data": "f190", "did": 0xF190}
        req = StepRequest.from_dict(data)
        assert req.sid == 0x22
        assert req.data == b"\xf1\x90"
        assert req.did == 0xF190

    def test_from_dict_minimal(self):
        data = {"sid": 0x10, "data": "01"}
        req = StepRequest.from_dict(data)
        assert req.sid == 0x10
        assert req.data == b"\x01"
        assert req.did is None


class TestStepExpect:
    """Tests for StepExpect dataclass."""

    def test_default_values(self):
        expect = StepExpect()
        assert expect.positive is True
        assert expect.nrc is None
        assert expect.data is None
        assert expect.did is None

    def test_positive_response(self):
        expect = StepExpect(positive=True, data=b"\x50\x01")
        assert expect.positive is True
        assert expect.data == b"\x50\x01"

    def test_negative_response(self):
        expect = StepExpect(positive=False, nrc=0x12)
        assert expect.positive is False
        assert expect.nrc == 0x12

    def test_to_dict(self):
        expect = StepExpect(positive=True, data=b"\x50\x01", did=0xF190)
        result = expect.to_dict()
        assert result["positive"] is True
        assert result["data"] == "5001"
        assert result["did"] == 0xF190
        assert result["nrc"] is None

    def test_from_dict(self):
        data = {"positive": True, "data": "5001", "did": 0xF190}
        expect = StepExpect.from_dict(data)
        assert expect.positive is True
        assert expect.data == b"\x50\x01"
        assert expect.did == 0xF190

    def test_from_dict_negative(self):
        data = {"positive": False, "nrc": 0x12}
        expect = StepExpect.from_dict(data)
        assert expect.positive is False
        assert expect.nrc == 0x12


class TestTestStep:
    """Tests for TestStep dataclass."""

    def test_create_step(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="session_switch", request=req, expect=expect)
        assert step.name == "session_switch"
        assert step.request == req
        assert step.expect == expect
        assert step.on_fail == "abort"

    def test_on_fail_continue(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="test", request=req, expect=expect, on_fail="continue")
        assert step.on_fail == "continue"

    def test_to_dict(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="session_switch", request=req, expect=expect)
        result = step.to_dict()
        assert result["name"] == "session_switch"
        assert result["request"]["sid"] == 0x10
        assert result["expect"]["positive"] is True
        assert result["on_fail"] == "abort"

    def test_from_dict(self):
        data = {
            "name": "session_switch",
            "request": {"sid": 0x10, "data": "01"},
            "expect": {"positive": True},
            "on_fail": "continue",
        }
        step = TestStep.from_dict(data)
        assert step.name == "session_switch"
        assert step.request.sid == 0x10
        assert step.expect.positive is True
        assert step.on_fail == "continue"

    def test_from_dict_minimal(self):
        data = {
            "name": "test",
            "request": {"sid": 0x10, "data": "01"},
            "expect": {},
        }
        step = TestStep.from_dict(data)
        assert step.name == "test"
        assert step.on_fail == "abort"


class TestCaseModel:
    """Tests for TestCase dataclass."""

    def test_create_test_case(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="session_switch", request=req, expect=expect)
        tc = TestCase(name="test_session", steps=[step])
        assert tc.name == "test_session"
        assert len(tc.steps) == 1
        assert tc.description is None

    def test_with_description(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="session_switch", request=req, expect=expect)
        tc = TestCase(name="test_session", steps=[step], description="Test session switch")
        assert tc.description == "Test session switch"

    def test_validate_empty_name(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="test", request=req, expect=expect)
        tc = TestCase(name="", steps=[step])
        errors = tc.validate()
        assert any("name" in e for e in errors)

    def test_validate_no_steps(self):
        tc = TestCase(name="test", steps=[])
        errors = tc.validate()
        assert any("step" in e for e in errors)

    def test_validate_valid(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="test", request=req, expect=expect)
        tc = TestCase(name="test", steps=[step])
        assert tc.validate() == []

    def test_to_dict(self):
        req = StepRequest(sid=0x10, data=b"\x01")
        expect = StepExpect(positive=True)
        step = TestStep(name="session_switch", request=req, expect=expect)
        tc = TestCase(name="test_session", steps=[step], description="Test")
        result = tc.to_dict()
        assert result["name"] == "test_session"
        assert result["description"] == "Test"
        assert len(result["steps"]) == 1

    def test_from_dict(self):
        data = {
            "name": "test_session",
            "description": "Test",
            "steps": [
                {
                    "name": "session_switch",
                    "request": {"sid": 0x10, "data": "01"},
                    "expect": {"positive": True},
                }
            ],
        }
        tc = TestCase.from_dict(data)
        assert tc.name == "test_session"
        assert tc.description == "Test"
        assert len(tc.steps) == 1
        assert tc.steps[0].name == "session_switch"


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_passed_result(self):
        result = StepResult(
            step_name="session_switch",
            passed=True,
            request_data=b"\x10\x01",
            response_data=b"\x50\x01",
        )
        assert result.step_name == "session_switch"
        assert result.passed is True
        assert result.request_data == b"\x10\x01"
        assert result.response_data == b"\x50\x01"
        assert result.error_message is None
        assert result.nrc is None

    def test_failed_result(self):
        result = StepResult(
            step_name="read_did",
            passed=False,
            request_data=b"\x22\xf1\x90",
            response_data=b"\x7f\x22\x12",
            nrc=0x12,
            error_message="SubFunctionNotSupported",
        )
        assert result.passed is False
        assert result.nrc == 0x12
        assert result.error_message == "SubFunctionNotSupported"

    def test_to_dict(self):
        result = StepResult(
            step_name="test",
            passed=True,
            request_data=b"\x10\x01",
            response_data=b"\x50\x01",
        )
        d = result.to_dict()
        assert d["step_name"] == "test"
        assert d["passed"] is True
        assert d["request_data"] == "1001"
        assert d["response_data"] == "5001"
        assert d["nrc"] is None

    def test_from_dict(self):
        d = {
            "step_name": "test",
            "passed": True,
            "request_data": "1001",
            "response_data": "5001",
        }
        result = StepResult.from_dict(d)
        assert result.step_name == "test"
        assert result.passed is True
        assert result.request_data == b"\x10\x01"
        assert result.response_data == b"\x50\x01"


class TestSessionRecord:
    """Tests for SessionRecord dataclass."""

    def test_create_session(self):
        session = SessionRecord(session_id="sess-001")
        assert session.session_id == "sess-001"
        assert session.transport_type == "doip"
        assert session.results == []
        assert session.start_time is not None
        assert session.end_time is None

    def test_add_result(self):
        session = SessionRecord(session_id="sess-001")
        result = StepResult(
            step_name="test",
            passed=True,
            request_data=b"\x10\x01",
            response_data=b"\x50\x01",
        )
        session.add_result(result)
        assert len(session.results) == 1
        assert session.results[0] == result

    def test_passed_all(self):
        session = SessionRecord(session_id="sess-001")
        session.add_result(
            StepResult(step_name="s1", passed=True, request_data=b"", response_data=b"")
        )
        session.add_result(
            StepResult(step_name="s2", passed=True, request_data=b"", response_data=b"")
        )
        assert session.passed is True

    def test_passed_with_failure(self):
        session = SessionRecord(session_id="sess-001")
        session.add_result(
            StepResult(step_name="s1", passed=True, request_data=b"", response_data=b"")
        )
        session.add_result(
            StepResult(step_name="s2", passed=False, request_data=b"", response_data=b"")
        )
        assert session.passed is False

    def test_passed_empty(self):
        session = SessionRecord(session_id="sess-001")
        assert session.passed is False

    def test_finalize(self):
        session = SessionRecord(session_id="sess-001")
        assert session.end_time is None
        session.finalize()
        assert session.end_time is not None

    def test_to_dict(self):
        session = SessionRecord(session_id="sess-001", transport_type="can")
        session.add_result(
            StepResult(step_name="test", passed=True, request_data=b"\x10", response_data=b"\x50")
        )
        d = session.to_dict()
        assert d["session_id"] == "sess-001"
        assert d["transport_type"] == "can"
        assert len(d["results"]) == 1

    def test_from_dict(self):
        d = {
            "session_id": "sess-001",
            "transport_type": "doip",
            "start_time": "2026-06-21T10:00:00",
            "end_time": "2026-06-21T10:00:01",
            "results": [
                {"step_name": "test", "passed": True, "request_data": "10", "response_data": "50"}
            ],
        }
        session = SessionRecord.from_dict(d)
        assert session.session_id == "sess-001"
        assert session.transport_type == "doip"
        assert len(session.results) == 1


class TestReportSummary:
    """Tests for ReportSummary dataclass."""

    def test_summary(self):
        summary = ReportSummary(total=10, passed=8, failed=2)
        assert summary.total == 10
        assert summary.passed == 8
        assert summary.failed == 2

    def test_pass_rate(self):
        summary = ReportSummary(total=10, passed=8, failed=2)
        assert summary.pass_rate == 80.0

    def test_pass_rate_all_passed(self):
        summary = ReportSummary(total=5, passed=5, failed=0)
        assert summary.pass_rate == 100.0

    def test_pass_rate_zero_total(self):
        summary = ReportSummary(total=0, passed=0, failed=0)
        assert summary.pass_rate == 0.0


class TestReport:
    """Tests for Report dataclass."""

    def test_create_report(self):
        session = SessionRecord(session_id="sess-001")
        session.add_result(
            StepResult(step_name="test", passed=True, request_data=b"\x10", response_data=b"\x50")
        )
        session.finalize()
        report = Report(test_case_name="test_case", session=session)
        assert report.test_case_name == "test_case"
        assert report.session == session
        assert report.summary.total == 1
        assert report.summary.passed == 1
        assert report.summary.failed == 0

    def test_report_with_failures(self):
        session = SessionRecord(session_id="sess-001")
        session.add_result(
            StepResult(step_name="s1", passed=True, request_data=b"\x10", response_data=b"\x50")
        )
        session.add_result(
            StepResult(step_name="s2", passed=False, request_data=b"\x22", response_data=b"\x7f")
        )
        session.finalize()
        report = Report(test_case_name="test_case", session=session)
        assert report.summary.total == 2
        assert report.summary.passed == 1
        assert report.summary.failed == 1

    def test_to_dict(self):
        session = SessionRecord(session_id="sess-001")
        session.add_result(
            StepResult(step_name="test", passed=True, request_data=b"\x10", response_data=b"\x50")
        )
        session.finalize()
        report = Report(test_case_name="test_case", session=session)
        d = report.to_dict()
        assert d["test_case_name"] == "test_case"
        assert d["summary"]["total"] == 1
        assert "session" in d

    def test_from_dict(self):
        d = {
            "test_case_name": "test_case",
            "session": {
                "session_id": "sess-001",
                "transport_type": "doip",
                "start_time": "2026-06-21T10:00:00",
                "end_time": "2026-06-21T10:00:01",
                "results": [
                    {
                        "step_name": "test",
                        "passed": True,
                        "request_data": "10",
                        "response_data": "50",
                    }
                ],
            },
        }
        report = Report.from_dict(d)
        assert report.test_case_name == "test_case"
        assert report.summary.total == 1
