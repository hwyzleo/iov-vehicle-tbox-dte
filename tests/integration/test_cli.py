"""Integration tests for DTE CLI."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dte.cli import main


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def profile_file(tmp_path: Path) -> Path:
    """Create a sample transport profile config file."""
    content = {
        "profiles": {
            "test_doip": {
                "transport_type": "doip",
                "doip": {
                    "target_ip": "192.168.1.100",
                    "tcp_port": 13401,
                },
            }
        }
    }
    config_file = tmp_path / "profile.json"
    config_file.write_text(json.dumps(content))
    return config_file


@pytest.fixture
def case_file(tmp_path: Path) -> Path:
    """Create a sample test case file."""
    content = {
        "id": "TC-001",
        "name": "Basic Read DID",
        "on_failure": "abort",
        "steps": [
            {
                "id": "S1",
                "description": "Read VIN",
                "request": {"service": 0x22, "did": 0xF190, "data": ""},
                "expect": {"success": True, "sid": 0x62},
            }
        ],
    }
    case_file = tmp_path / "test_case.json"
    case_file.write_text(json.dumps(content))
    return case_file


@pytest.fixture
def case_file_with_profile_ref(tmp_path: Path) -> Path:
    """Create a test case file with profile_ref."""
    content = {
        "id": "TC-002",
        "name": "Profile Ref Test",
        "profile_ref": "test_doip",
        "steps": [
            {
                "id": "S1",
                "request": {"service": 0x22, "did": 0xF190, "data": ""},
                "expect": {"success": True},
            }
        ],
    }
    case_file = tmp_path / "case_ref.json"
    case_file.write_text(json.dumps(content))
    return case_file


class TestCLIBasic:
    """Tests for basic CLI functionality."""

    def test_main_help(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "TBOX Diagnostic Tester Emulator" in result.output

    def test_version(self, runner: CliRunner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "dte" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_profile(self, runner: CliRunner, profile_file: Path):
        result = runner.invoke(main, ["validate", str(profile_file)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "Valid" in result.output

    def test_validate_with_profile_name(self, runner: CliRunner, profile_file: Path):
        result = runner.invoke(main, ["validate", str(profile_file), "--name", "test_doip"])
        assert result.exit_code == 0

    def test_validate_nonexistent_profile_name(self, runner: CliRunner, profile_file: Path):
        result = runner.invoke(main, ["validate", str(profile_file), "--name", "nonexistent"])
        assert result.exit_code != 0

    def test_validate_invalid_profile(self, runner: CliRunner, tmp_path: Path):
        content = {
            "profiles": {
                "bad_profile": {
                    "transport_type": "doip",
                    "doip": {"target_ip": "", "tcp_port": 99999},
                }
            }
        }
        config_file = tmp_path / "bad.json"
        config_file.write_text(json.dumps(content))
        result = runner.invoke(main, ["validate", str(config_file)])
        assert result.exit_code != 0

    def test_validate_nonexistent_file(self, runner: CliRunner):
        result = runner.invoke(main, ["validate", "/nonexistent/profile.json"])
        assert result.exit_code != 0


class TestRunCommand:
    """Tests for the run command."""

    def test_run_with_profile(self, runner: CliRunner, case_file: Path, profile_file: Path):
        with patch("dte.cli.ScenarioEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine
            step_result = MagicMock()
            step_result.verdict = "pass"
            step_result.step_id = "S1"
            step_result.duration_ms = 1.5
            mock_engine.execute_test_case.return_value = MagicMock(
                step_results=[step_result],
                state="completed",
                passed=True,
            )
            result = runner.invoke(
                main, ["run", str(case_file), "--profile", str(profile_file)]
            )
            assert result.exit_code == 0

    def test_run_missing_case_file(self, runner: CliRunner, profile_file: Path):
        result = runner.invoke(
            main, ["run", "/nonexistent/case.json", "--profile", str(profile_file)]
        )
        assert result.exit_code != 0

    def test_run_missing_profile(self, runner: CliRunner, case_file: Path):
        result = runner.invoke(main, ["run", str(case_file)])
        assert result.exit_code != 0

    def test_run_with_output_json(self, runner: CliRunner, case_file: Path, profile_file: Path):
        with patch("dte.cli.ScenarioEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine
            step_result = MagicMock()
            step_result.verdict = "pass"
            step_result.step_id = "S1"
            step_result.duration_ms = 1.5
            mock_record = MagicMock()
            mock_record.step_results = [step_result]
            mock_record.state = "completed"
            mock_record.passed = True
            mock_record.to_dict.return_value = {"session_id": "TC-001", "state": "completed"}
            mock_engine.execute_test_case.return_value = mock_record
            result = runner.invoke(
                main,
                ["run", str(case_file), "--profile", str(profile_file), "--output", "json"],
            )
            assert result.exit_code == 0


class TestConnectCommand:
    """Tests for the connect command."""

    def test_connect_requires_profile(self, runner: CliRunner):
        result = runner.invoke(main, ["connect"])
        assert result.exit_code != 0

    def test_connect_with_profile(self, runner: CliRunner, profile_file: Path):
        with patch("dte.cli.create_transport") as mock_create:
            mock_transport = MagicMock()
            mock_transport.is_connected = False
            mock_create.return_value = mock_transport
            result = runner.invoke(main, ["connect", "--profile", str(profile_file)])
            assert result.exit_code == 0

    def test_connect_nonexistent_profile(self, runner: CliRunner):
        result = runner.invoke(main, ["connect", "--profile", "/nonexistent/profile.json"])
        assert result.exit_code != 0
