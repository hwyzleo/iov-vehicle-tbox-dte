"""Tests for assertion engine."""
from __future__ import annotations

from dte.engine.assertion import AssertionEngine, AssertionResult
from dte.model.test_step import StepExpect
from dte.uds.client import UDSResponse


class TestAssertionResult:
    """Tests for AssertionResult dataclass."""

    def test_pass_result(self):
        result = AssertionResult(verdict="pass")
        assert result.verdict == "pass"
        assert result.error_message is None

    def test_fail_result_with_message(self):
        result = AssertionResult(verdict="fail", error_message="NRC mismatch")
        assert result.verdict == "fail"
        assert result.error_message == "NRC mismatch"


class TestAssertionEngine:
    """Tests for AssertionEngine.assert_response."""

    def test_positive_response_expected_positive(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=True)
        result = engine.assert_response(response, expect)
        assert result.verdict == "pass"

    def test_positive_response_expected_negative(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=False)
        result = engine.assert_response(response, expect)
        assert result.verdict == "fail"
        assert "positive" in result.error_message.lower()

    def test_negative_response_expected_positive(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x22\x31",
            raw=b"\x7F\x22\x31",
            nrc=0x31,
        )
        expect = StepExpect(success=True)
        result = engine.assert_response(response, expect)
        assert result.verdict == "fail"
        assert "negative" in result.error_message.lower()

    def test_negative_response_expected_negative(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x22\x31",
            raw=b"\x7F\x22\x31",
            nrc=0x31,
        )
        expect = StepExpect(success=False)
        result = engine.assert_response(response, expect)
        assert result.verdict == "pass"

    def test_nrc_match_pass(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x22\x31",
            raw=b"\x7F\x22\x31",
            nrc=0x31,
        )
        expect = StepExpect(success=False, nrc=0x31)
        result = engine.assert_response(response, expect)
        assert result.verdict == "pass"

    def test_nrc_mismatch_fail(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x7F,
            positive=False,
            data=b"\x22\x31",
            raw=b"\x7F\x22\x31",
            nrc=0x31,
        )
        expect = StepExpect(success=False, nrc=0x22)
        result = engine.assert_response(response, expect)
        assert result.verdict == "fail"
        assert "nrc" in result.error_message.lower()

    def test_sid_match_pass(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=True, sid=0x62)
        result = engine.assert_response(response, expect)
        assert result.verdict == "pass"

    def test_sid_mismatch_fail(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=True, sid=0x50)
        result = engine.assert_response(response, expect)
        assert result.verdict == "fail"
        assert "sid" in result.error_message.lower()

    def test_no_expect_constraints_pass(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"",
            raw=b"\x62",
        )
        expect = StepExpect()
        result = engine.assert_response(response, expect)
        assert result.verdict == "pass"

    def test_nrc_none_on_positive_response(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"",
            raw=b"\x62",
        )
        expect = StepExpect(success=True, nrc=None)
        result = engine.assert_response(response, expect)
        assert result.verdict == "pass"

    def test_did_data_match_pass(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=True, did_data_match=True)
        result = engine.assert_response(response, expect, request_data=b"\xF1\x90VIN")
        assert result.verdict == "pass"

    def test_did_data_match_fail(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90BAD",
            raw=b"\x62\xF1\x90BAD",
        )
        expect = StepExpect(success=True, did_data_match=True)
        result = engine.assert_response(response, expect, request_data=b"\xF1\x90VIN")
        assert result.verdict == "fail"
        assert "did data mismatch" in result.error_message.lower()

    def test_did_data_no_match_pass(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90OTHER",
            raw=b"\x62\xF1\x90OTHER",
        )
        expect = StepExpect(success=True, did_data_match=False)
        result = engine.assert_response(response, expect, request_data=b"\xF1\x90VIN")
        assert result.verdict == "pass"

    def test_did_data_no_match_fail(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=True, did_data_match=False)
        result = engine.assert_response(response, expect, request_data=b"\xF1\x90VIN")
        assert result.verdict == "fail"
        assert "should not match" in result.error_message.lower()

    def test_did_data_match_none_skips_check(self):
        engine = AssertionEngine()
        response = UDSResponse(
            service_id=0x62,
            positive=True,
            data=b"\xF1\x90VIN",
            raw=b"\x62\xF1\x90VIN",
        )
        expect = StepExpect(success=True, did_data_match=None)
        result = engine.assert_response(response, expect, request_data=b"\xF1\x90OTHER")
        assert result.verdict == "pass"
