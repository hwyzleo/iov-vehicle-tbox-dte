"""UDS service definitions - enums for session types, security access, etc."""
from __future__ import annotations

from enum import IntEnum


class DiagnosticSessionType(IntEnum):
    """UDS session types (0x10 sub-functions)."""

    DEFAULT = 0x01
    PROGRAMMING = 0x02
    EXTENDED = 0x03
    SAFETY_SYSTEM = 0x04


class SecurityAccessType(IntEnum):
    """UDS security access levels (0x27 sub-functions)."""

    LEVEL_1_REQUEST_SEED = 0x01
    LEVEL_1_SEND_KEY = 0x02
    LEVEL_3_REQUEST_SEED = 0x03
    LEVEL_3_SEND_KEY = 0x04
    LEVEL_5_REQUEST_SEED = 0x05
    LEVEL_5_SEND_KEY = 0x06
    LEVEL_7_REQUEST_SEED = 0x07
    LEVEL_7_SEND_KEY = 0x08


class RoutineControlType(IntEnum):
    """Routine control sub-functions (0x31)."""

    START = 0x01
    STOP = 0x02
    REQUEST_RESULTS = 0x03


class DTCSubFunction(IntEnum):
    """Read DTC sub-functions (0x19)."""

    REPORT_NUMBER = 0x01
    REPORT_BY_STATUS_MASK = 0x02
    REPORT_DTC_SNAPSHOT = 0x03
    REPORT_DTC_SNAPSHOT_BY_DTC = 0x04
    REPORT_DTC_EXTENDED = 0x06
    REPORT_SUPPORTED_DTC = 0x0A


class IOControlType(IntEnum):
    """IO Control sub-functions (0x2F)."""

    RETURN_CONTROL_TO_ECU = 0x00
    RESET_TO_DEFAULT = 0x01
    FREEZE_CURRENT_STATE = 0x02
    SHORT_TERM_ADJUSTMENT = 0x03


class NegativeResponseCode(IntEnum):
    """UDS negative response codes (NRC)."""

    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUB_FUNCTION_NOT_SUPPORTED = 0x12
    INCORRECT_MESSAGE_LENGTH_OR_INVALID_FORMAT = 0x13
    RESPONSE_TOO_LONG = 0x14
    BUSY_REPEAT_REQUEST = 0x21
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    NO_RESPONSE_FROM_SUBNET_COMPONENT = 0x25
    FAILURE_PREVENTS_EXECUTION_OF_REQUESTED_ACTION = 0x26
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEEDED_NUMBER_OF_ATTEMPTS = 0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED = 0x37
    UPLOAD_DOWNLOAD_NOT_ACCEPTED = 0x70
    TRANSFER_DATA_SUSPENDED = 0x71
    GENERAL_PROGRAMMING_FAILURE = 0x72
    RESPONSE_PENDING = 0x78
    SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7F
