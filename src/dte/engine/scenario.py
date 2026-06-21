"""Scenario engine for orchestrating test execution."""
from __future__ import annotations

import logging

from dte.engine.executor import ScriptExecutor
from dte.model.report import Report
from dte.model.test_case import TestCase
from dte.transport.base import BaseTransport
from dte.uds.client import TransportConnection, UDSClient

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Coordinates transport, UDS client, and executor to run test scenarios."""

    def __init__(self, executor: ScriptExecutor | None = None) -> None:
        self._executor = executor or ScriptExecutor()

    def _create_client(self, transport: BaseTransport) -> UDSClient:
        """Create a UDSClient connected via the given transport.

        Args:
            transport: Connected transport instance.

        Returns:
            Configured UDSClient.
        """
        conn = TransportConnection(transport)
        return UDSClient(conn=conn)

    def run(self, transport: BaseTransport, test_cases: list[TestCase]) -> Report:
        """Execute test cases against a transport.

        Args:
            transport: Transport to use for communication.
            test_cases: List of test cases to execute.

        Returns:
            Report with session records and exit code.
        """
        if not transport.is_connected:
            transport.connect()

        client = self._create_client(transport)

        try:
            report = Report(session_id="scenario")

            for case in test_cases:
                logger.info("Running test case: %s", case.name)
                record = self._executor.run_test_case(client, case)
                report.session_records.append(record)

            report.exit_code = 0 if report.summary.failed == 0 else 1
            return report
        finally:
            transport.disconnect()
