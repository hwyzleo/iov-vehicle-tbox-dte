# API Reference

## Config Module

### `dte.config.loader`

#### `load_config(path: Path) -> dict[str, TransportProfile]`

Load transport profiles from a YAML or JSON config file.

**Parameters:**
- `path` -- path to config file (`.yaml`, `.yml`, or `.json`)

**Returns:** dict mapping profile name to `TransportProfile`

**Raises:** `ConfigLoaderError` on file not found or parse failure.

### `dte.config.transport_profile`

#### `TransportType` (Enum)

- `TransportType.DOIP` -- Diagnostics over IP
- `TransportType.CAN` -- CAN/ISO-TP

#### `CANAddressing` (Enum)

- `CANAddressing.NORMAL` -- standard 11-bit
- `CANAddressing.EXTENDED` -- extended 11-bit
- `CANAddressing.MIXED` -- mixed 29-bit

#### `DoIPConfig` (frozen dataclass)

| Field | Type | Default |
|-------|------|---------|
| `target_ip` | `str` | `"localhost"` |
| `tcp_port` | `int` | `13400` |
| `udp_port` | `int` | `13400` |
| `source_addr` | `int` | `0x0E00` |
| `target_addr` | `int` | `0x0010` |
| `activation_type` | `int` | `0x00` |
| `discovery` | `bool` | `True` |

#### `CANConfig` (frozen dataclass)

| Field | Type | Default |
|-------|------|---------|
| `interface` | `str` | `"socketcan"` |
| `channel` | `str` | `"can0"` |
| `bitrate` | `int` | `500000` |
| `addressing` | `CANAddressing` | `NORMAL` |
| `req_id` | `int` | `0x7E0` |
| `resp_id` | `int` | `0x7E8` |
| `func_id` | `int` | `0x7DF` |
| `block_size` | `int` | `0` |
| `st_min` | `int` | `0` |

#### `TimingConfig` (frozen dataclass)

| Field | Type | Default |
|-------|------|---------|
| `p2` | `float` | `5.0` |
| `p2_star` | `float` | `5000.0` |
| `n_as` | `float` | `1.0` |
| `n_ar` | `float` | `1.0` |
| `n_bs` | `float` | `1.0` |
| `n_cr` | `float` | `1.0` |

#### `TransportProfile` (frozen dataclass)

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | (required) |
| `transport_type` | `TransportType` | `DOIP` |
| `doip` | `DoIPConfig` | `DoIPConfig()` |
| `can` | `CANConfig` | `CANConfig()` |
| `timing` | `TimingConfig` | `TimingConfig()` |

**Methods:**

- `validate() -> list[str]` -- returns list of validation errors (empty if valid)
- `to_dict() -> dict[str, Any]` -- serialize to dict
- `from_dict(data: dict) -> TransportProfile` -- class method, deserialize from dict

---

## Transport Module

### `dte.transport.base`

#### `BaseTransport` (ABC)

Abstract base for all transport implementations.

**Properties:**
- `profile -> TransportProfile` -- the transport's profile config
- `is_connected -> bool` -- connection state

**Methods:**
- `connect() -> None` -- establish connection
- `disconnect() -> None` -- close connection
- `send_recv(data: bytes, timeout: float = 5.0) -> bytes` -- send UDS request, receive response

Supports context manager (`with` statement).

### `dte.transport.doip`

#### `DoIPTransport(BaseTransport)`

DoIP transport using `doipclient` library.

**Constructor:** `DoIPTransport(config: DoIPConfig, profile: TransportProfile | None = None)`

### `dte.transport.can`

#### `CANTransport(BaseTransport)`

CAN/ISO-TP transport using `python-can` and `can-isotp`.

**Constructor:** `CANTransport(config: CANConfig, profile: TransportProfile | None = None)`

### `dte.transport.factory`

#### `create_transport(profile: TransportProfile) -> BaseTransport`

Factory function. Creates `DoIPTransport` or `CANTransport` based on `profile.transport_type`.

**Raises:** `ValueError` for unsupported transport types.

### `dte.transport.exceptions`

- `TransportError` -- base exception
- `ConnectionError(TransportError)` -- connection failures
- `TimeoutError(TransportError)` -- operation timeouts

---

## UDS Module

### `dte.uds.client`

#### `UDSResponse` (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `service_id` | `int` | Response SID (`0x7F` for negative) |
| `positive` | `bool` | Whether response is positive |
| `data` | `bytes` | Payload (excluding SID) |
| `raw` | `bytes` | Full raw response bytes |
| `nrc` | `int \| None` | Negative response code |

#### `TransportConnection(BaseConnection)`

Adapter bridging `BaseTransport` to udsoncan's `BaseConnection`.

**Constructor:** `TransportConnection(transport: BaseTransport, name: str | None = None)`

#### `UDSClient`

Main UDS client wrapper.

**Constructor:** `UDSClient(conn=None, security_adapter=None, config=None)`

- `conn` -- `BaseConnection` or `BaseTransport` instance
- `security_adapter` -- `SecurityAccessAdapter` for seed-to-key
- `config` -- optional udsoncan `ClientConfig`

**Methods:**

| Method | UDS Service | Returns |
|--------|-------------|---------|
| `session_control(session_type: int)` | `0x10` | `UDSResponse` |
| `read_did(did: int)` | `0x22` | `UDSResponse` |
| `write_did(did: int, data: bytes)` | `0x2E` | `UDSResponse` |
| `security_access(level: int, seed_to_key: bytes = b"")` | `0x27` | `UDSResponse` |
| `routine_control(routine_id: int, control_type: int, data: bytes = None)` | `0x31` | `UDSResponse` |
| `read_dtc(status_mask: int)` | `0x19` | `UDSResponse` |
| `clear_dtc(group: int = 0xFFFFFF)` | `0x14` | `UDSResponse` |
| `io_control(did: int, control_type: int = 0x03, data=None)` | `0x2F` | `UDSResponse` |
| `set_connection(conn)` | -- | `None` |

Supports context manager.

**Raises:** `UDSError` on client errors.

### `dte.uds.security`

#### `SecurityAccessAdapter` (ABC)

Abstract base for seed-to-key adapters.

**Method:** `compute_key(seed: bytes, level: int) -> bytes`

#### `FixedKeyAdapter(SecurityAccessAdapter)`

Returns a fixed key regardless of seed.

**Constructor:** `FixedKeyAdapter(key: bytes)`

#### `XORAdapter(SecurityAccessAdapter)`

XORs seed with configured key (cyclically).

**Constructor:** `XORAdapter(key: bytes)`

#### `CallableAdapter(SecurityAccessAdapter)`

Delegates to a user-provided `fn(seed, level) -> bytes`.

**Constructor:** `CallableAdapter(fn: Callable[[bytes, int], bytes])`

#### `create_adapter(adapter_type: str, key: bytes = b"", fn=None) -> SecurityAccessAdapter`

Factory for adapters. `adapter_type`: `"fixed"`, `"xor"`, or `"callable"`.

### `dte.uds.services`

Enum classes:

- `DiagnosticSessionType` -- `DEFAULT(1)`, `PROGRAMMING(2)`, `EXTENDED(3)`, `SAFETY_SYSTEM(4)`
- `SecurityAccessType` -- seed/key levels (1-8)
- `RoutineControlType` -- `START(1)`, `STOP(2)`, `REQUEST_RESULTS(3)`
- `DTCSubFunction` -- `REPORT_NUMBER(1)`, `REPORT_BY_STATUS_MASK(2)`, `REPORT_DTC_SNAPSHOT(3)`, etc.
- `IOControlType` -- `RETURN_CONTROL_TO_ECU(0)`, `RESET_TO_DEFAULT(1)`, `FREEZE_CURRENT_STATE(2)`, `SHORT_TERM_ADJUSTMENT(3)`
- `NegativeResponseCode` -- all standard UDS NRC values

---

## Model Module

### `dte.model.test_step`

#### `StepRequest` (dataclass)

| Field | Type | Default |
|-------|------|---------|
| `service` | `int` | (required) |
| `did` | `int \| None` | `None` |
| `data` | `bytes` | `b""` |
| `routine_id` | `int \| None` | `None` |
| `control_type` | `int \| None` | `None` |
| `sub_function` | `int \| None` | `None` |

Methods: `to_dict()`, `from_dict(data)`

#### `StepExpect` (dataclass)

| Field | Type | Default |
|-------|------|---------|
| `sid` | `int \| None` | `None` |
| `success` | `bool` | `True` |
| `nrc` | `int \| None` | `None` |
| `did_data_match` | `bool \| None` | `None` |

Methods: `to_dict()`, `from_dict(data)`

#### `TestStep` (dataclass)

| Field | Type |
|-------|------|
| `id` | `str` |
| `request` | `StepRequest` |
| `expect` | `StepExpect` |
| `description` | `str \| None` |

Methods: `to_dict()`, `from_dict(data)`

### `dte.model.test_case`

#### `TestCase` (dataclass)

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | (required) |
| `name` | `str` | (required) |
| `steps` | `list[TestStep]` | `[]` |
| `profile_ref` | `str \| None` | `None` |
| `on_failure` | `str` | `"abort"` |

Methods: `validate() -> list[str]`, `to_dict()`, `from_dict(data)`

### `dte.model.session`

#### `StepResult` (dataclass)

| Field | Type |
|-------|------|
| `step_id` | `str` |
| `verdict` | `str` (`"pass"`, `"fail"`, `"error"`) |
| `request_bytes` | `bytes` |
| `response_bytes` | `bytes` |
| `parsed` | `dict \| None` |
| `timestamp` | `str \| None` |
| `duration_ms` | `float \| None` |
| `nrc` | `int \| None` |
| `error_message` | `str \| None` |

Methods: `to_dict()`, `from_dict(data)`

#### `SessionRecord` (dataclass)

| Field | Type |
|-------|------|
| `session_id` | `str` |
| `transport` | `str` |
| `profile` | `str \| None` |
| `state` | `str` |
| `step_results` | `list[StepResult]` |
| `frames` | `list[dict]` |
| `started_at` | `str \| None` |
| `ended_at` | `str \| None` |

**Properties:** `passed -> bool` (all steps passed)

**Methods:** `add_step_result(result)`, `add_frame(frame)`, `finalize()`, `to_dict()`, `from_dict(data)`

### `dte.model.report`

#### `ReportSummary` (dataclass)

| Field | Type |
|-------|------|
| `total` | `int` |
| `passed` | `int` |
| `failed` | `int` |
| `errors` | `int` |
| `skipped` | `int` |
| `duration_ms` | `float \| None` |

**Property:** `success_rate -> float` (percentage)

#### `Report` (dataclass)

| Field | Type |
|-------|------|
| `session_id` | `str` |
| `exit_code` | `int` |
| `session_records` | `list[SessionRecord]` |

**Property:** `summary -> ReportSummary`

**Class method:** `from_session_records(session_id, exit_code, records)`

Methods: `to_dict()`, `from_dict(data)`

---

## Engine Module

### `dte.engine.scenario`

#### `ScenarioEngine`

Orchestrates test execution.

**Constructor:** `ScenarioEngine(executor: ScriptExecutor | None = None)`

**Methods:**

- `execute_test_case(test_case, transport_profile) -> SessionRecord` -- run one test case
- `execute_test_suite(test_cases, transport_profile) -> Report` -- run multiple test cases
- `run(transport, test_cases) -> Report` -- run against an existing transport

### `dte.engine.executor`

#### `ScriptExecutor`

Executes test steps against a UDS client.

**Constructor:** `ScriptExecutor(assertion_engine: AssertionEngine | None = None)`

**Methods:**

- `run_step(client: UDSClient, step: TestStep) -> StepResult` -- execute one step
- `execute_test_case(test_case, transport_profile) -> SessionRecord` -- full lifecycle (connect, run, disconnect)
- `run_test_case(client, case) -> SessionRecord` -- run with existing client

### `dte.engine.assertion`

#### `AssertionResult` (dataclass)

| Field | Type |
|-------|------|
| `verdict` | `str` (`"pass"` or `"fail"`) |
| `error_message` | `str \| None` |

#### `AssertionEngine`

Validates UDS responses.

**Method:** `assert_response(response: UDSResponse, expect: StepExpect, request_data: bytes = b"") -> AssertionResult`

Checks: positive/negative response match, NRC match, SID match, DID data match.
