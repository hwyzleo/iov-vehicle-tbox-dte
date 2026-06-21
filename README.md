# iov-vehicle-tbox-dte

TBOX Diagnostic Tester Emulator (DTE) -- a Python-based diagnostic tool for vehicle TBOX (Telematics Box) testing via UDS (Unified Diagnostic Services).

## Features

- **DoIP and CAN/ISO-TP transports** -- communicate with TBOX over Ethernet (DoIP) or CAN bus
- **UDS service support** -- session control, security access, DID read/write, DTC operations, routine control, I/O control
- **Test case execution** -- define test scenarios in YAML/JSON and execute them against a target
- **Assertion engine** -- validate UDS responses against expected outcomes
- **Interactive CLI** -- connect and send UDS commands interactively
- **Pluggable security adapters** -- fixed key, XOR, or custom callable-based seed-to-key computation

## Architecture

```
dte/
  cli.py              # CLI entry point (click)
  config/
    loader.py         # YAML/JSON config loader
    transport_profile.py  # Transport profile dataclasses
  transport/
    base.py           # Abstract transport interface
    doip.py           # DoIP transport (doipclient)
    can.py            # CAN/ISO-TP transport (python-can, can-isotp)
    factory.py        # Transport factory
  uds/
    client.py         # UDS client wrapper (udsoncan)
    security.py       # Security access adapters
    services.py       # UDS service enums and NRC codes
  model/
    test_case.py      # TestCase model
    test_step.py      # TestStep, StepRequest, StepExpect
    session.py        # SessionRecord, StepResult
    report.py         # Report, ReportSummary
  engine/
    scenario.py       # ScenarioEngine orchestrator
    executor.py       # ScriptExecutor step runner
    assertion.py      # AssertionEngine response validator
```

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd iov-vehicle-tbox-dte

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Requirements

- Python >= 3.10
- Runtime: `pyyaml`, `udsoncan`, `doipclient`, `python-can`, `can-isotp`, `click`, `rich`
- Dev: `pytest`, `pytest-cov`, `pytest-mock`, `mypy`, `ruff`

## Quick Start

### 1. Create a transport profile

```yaml
# profiles.yaml
profiles:
  my_doip:
    transport_type: doip
    doip:
      target_ip: "192.168.1.100"
      tcp_port: 13400
      source_addr: 0x0E00
      target_addr: 0x0010
```

### 2. Create a test case

```yaml
# read_vin.yaml
id: "READ-VIN-001"
name: "Read VIN"
on_failure: abort
steps:
  - id: "S01"
    description: "Switch to extended session"
    request:
      service: 0x10
      sub_function: 0x03
      data: ""
    expect:
      success: true
      sid: 0x50

  - id: "S02"
    description: "Read VIN"
    request:
      service: 0x22
      did: 0xF190
      data: ""
    expect:
      success: true
      sid: 0x62
```

### 3. Run the test

```bash
dte run read_vin.yaml --profile profiles.yaml --profile-name my_doip
```

### 4. Interactive mode

```bash
dte connect --profile profiles.yaml --profile-name my_doip
```

### 5. Validate a profile

```bash
dte validate profiles.yaml --name my_doip
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `dte run <case_file> --profile <file>` | Execute a test case |
| `dte connect --profile <file>` | Start interactive diagnostic session |
| `dte validate <profile_file>` | Validate a transport profile config |

Run `dte --help` or `dte <command> --help` for full usage.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dte --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

## Development

```bash
# Lint
ruff check src/ tests/

# Type check
mypy src/dte/
```

## License

Apache-2.0
