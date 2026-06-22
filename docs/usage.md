# Usage Guide

## Transport Profiles

A transport profile defines how DTE connects to a TBOX. Profiles are stored in YAML or JSON files under a `profiles` key.

### DoIP Profile

```yaml
profiles:
  doip_direct:
    transport_type: doip
    doip:
      target_ip: "192.168.1.100"
      tcp_port: 13400
      udp_port: 13400
      source_addr: 0x0E00
      target_addr: 0x0001
      activation_type: 0x00
      discovery: true
    timing:
      p2: 5.0
      p2_star: 5.0
```

### CAN Profile

```yaml
profiles:
  can_standard:
    transport_type: can
    can:
      interface: "socketcan"
      channel: "can0"
      bitrate: 500000
      addressing: normal
      req_id: 0x7E0
      resp_id: 0x7E8
      func_id: 0x7DF
      block_size: 0
      st_min: 0
    timing:
      p2: 5.0
      p2_star: 5.0
```

### CAN Addressing Modes

| Mode | Description |
|------|-------------|
| `normal` | Standard 11-bit CAN IDs |
| `extended` | Extended 11-bit addressing |
| `mixed` | Mixed 29-bit addressing |

## Test Cases

Test cases define a sequence of UDS steps with expected responses. They are stored in YAML or JSON files.

### Structure

```yaml
id: "TEST-001"
name: "My Test Case"
profile_ref: "doip_direct"    # references a profile name
on_failure: abort              # "abort" stops on failure, "continue" runs all steps
steps:
  - id: "S01"
    description: "Step description"
    request:
      service: 0x10            # UDS service ID
      sub_function: 0x03       # sub-function byte
      did: 0xF190              # DID (for 0x22, 0x2E, 0x2F)
      data: ""                 # hex string payload
      routine_id: 0xFF00       # routine ID (for 0x31)
      control_type: 0x01       # control type (for 0x31, 0x2F)
    expect:
      success: true            # true=positive, false=negative response expected
      sid: 0x50                # expected response service ID
      nrc: 0x33                # expected NRC (for negative responses)
      did_data_match: true     # DID echo data must match request
```

### Supported UDS Services

| Service | ID | Request Fields |
|---------|----|----------------|
| Session Control | `0x10` | `sub_function` (1=Default, 2=Programming, 3=Extended) |
| Read DID | `0x22` | `did` |
| Write DID | `0x2E` | `did`, `data` |
| Security Access | `0x27` | `sub_function` (odd=seed, even=key), `data` |
| Routine Control | `0x31` | `routine_id`, `control_type` (1=Start, 2=Stop, 3=Results), `data` |
| Read DTC | `0x19` | `data` (status mask byte) |
| Clear DTC | `0x14` | `data` (group, default `ffffff`) |
| I/O Control | `0x2F` | `did`, `control_type`, `data` |

### Example: EOL Provisioning

```yaml
id: "EOL-PROV-001"
name: "EOL Provisioning Test"
profile_ref: "doip_direct"
on_failure: abort
steps:
  - id: "EOL-P01"
    description: "Switch to extended session"
    request:
      service: 0x10
      sub_function: 0x03
      data: ""
    expect:
      success: true
      sid: 0x50

  - id: "EOL-P04"
    description: "Read VIN"
    request:
      service: 0x22
      did: 0xF190
      data: ""
    expect:
      success: true
      sid: 0x62

  - id: "EOL-P08"
    description: "Start EOL routine"
    request:
      service: 0x31
      routine_id: 0xFF00
      control_type: 0x01
      data: ""
    expect:
      success: true
      sid: 0x71
```

### Example: Negative Response Assertion

```yaml
  - id: "S03"
    description: "Expect security denied"
    request:
      service: 0x27
      sub_function: 0x02
      data: "00000000"
    expect:
      success: false
      nrc: 0x33
```

## CLI Reference

### `dte run`

Execute a test case against a target.

```bash
dte run <CASE_FILE> --profile <PROFILE_FILE> [--profile-name <NAME>] [--output text|json]
```

- `CASE_FILE` -- path to test case YAML/JSON file
- `--profile, -p` -- path to transport profile config file (required)
- `--profile-name, -n` -- profile name within config (default: first profile)
- `--output, -o` -- output format: `text` (table) or `json`

Exit code is `0` if all steps pass, `1` otherwise.

### `dte connect`

Start an interactive diagnostic session.

```bash
dte connect --profile <PROFILE_FILE> [--profile-name <NAME>]
```

Interactive commands:

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `status` | Show connection status |
| `session <type>` | Switch session (1=Default, 2=Programming, 3=Extended) |
| `read_did <hex>` | Read DID (e.g., `read_did F190`) |
| `write_did <hex> <hex_data>` | Write DID |
| `security <level>` | Security access |
| `routine <id> <type>` | Routine control |
| `read_dtc <mask>` | Read DTCs |
| `clear_dtc` | Clear all DTCs |
| `quit` / `exit` / `q` | Exit |

### `dte validate`

Validate a transport profile configuration.

```bash
dte validate <PROFILE_FILE> [--name <NAME>]
```

Reports validation errors for profile fields (IP, port ranges, CAN IDs, etc.).

## Python API Usage

```python
from dte.config.transport_profile import TransportProfile, TransportType, DoIPConfig
from dte.model.test_case import TestCase
from dte.model.test_step import TestStep, StepRequest, StepExpect
from dte.engine.scenario import ScenarioEngine
from dte.transport.factory import create_transport
from dte.uds.client import UDSClient, TransportConnection
from dte.uds.security import FixedKeyAdapter

# Create transport profile
profile = TransportProfile(
    name="my_doip",
    transport_type=TransportType.DOIP,
    doip=DoIPConfig(target_ip="192.168.1.100"),
)

# Run a test case via engine
engine = ScenarioEngine()
test_case = TestCase.from_dict({
    "id": "T1",
    "name": "Read VIN",
    "steps": [{
        "id": "S1",
        "request": {"service": 0x22, "did": 0xF190, "data": ""},
        "expect": {"success": True, "sid": 0x62},
    }],
})
record = engine.execute_test_case(test_case, profile)
print(record.passed, record.state)

# Direct UDS client usage
transport = create_transport(profile)
transport.connect()
conn = TransportConnection(transport)
client = UDSClient(conn=conn, security_adapter=FixedKeyAdapter(key=b"\xaa\xbb"))
client.session_control(0x03)
response = client.read_did(0xF190)
print(response.positive, response.data.hex())
transport.disconnect()
```
