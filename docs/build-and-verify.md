# TBOX DTE 构建与验证指南

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | >= 3.10 |
| 操作系统 | macOS / Linux |
| 对接目标 | iov-vehicle-tbox-diag 服务 |

## 安装依赖

```bash
cd /Users/hwyz_leo/Projects/open-iov/vehicle/tbox/iov-vehicle-tbox-dte

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate

# 安装运行时 + 开发依赖
pip install -e ".[dev]"
```

## 验证步骤

### 1. 运行单元测试

```bash
python -m pytest tests/ -v
```

预期输出：全部 PASSED，无 FAILED。

```bash
# 查看覆盖率
python -m pytest tests/ --cov=dte --cov-report=term-missing
```

### 2. 代码质量检查

```bash
# Lint
python -m ruff check src/

# 类型检查
python -m mypy src/dte/
```

预期输出：无错误。

### 3. CLI 可用性验证

```bash
# 查看帮助
dte --help

# 查看版本
dte --version

# 验证配置文件
dte validate tests/fixtures/transport_profiles/doip_direct.yaml
```

### 4. 对接 DIAG 服务验证

#### 前置条件

- DIAG 服务已编译并运行，监听在 `0.0.0.0:13400`
- DTE 所在网络能访问 DIAG 服务的 IP 地址

#### 准备传输配置

```yaml
# profiles.yaml
profiles:
  diag_test:
    transport_type: doip
    doip:
      target_ip: "DIAG服务IP地址"   # 替换为实际 IP
      tcp_port: 13400
      source_addr: 0x0E00
      target_addr: 0x0001          # 必须与 DIAG 的 local_address 一致
      activation_type: 0x00
    timing:
      p2: 5.0
      p2_star: 5.0
```

#### 交互式验证

```bash
dte connect --profile profiles.yaml --profile-name diag_test
```

进入交互模式后，根据业务场景执行对应的命令序列。

##### 场景一：EOL 写入 VIN（RID 0xFF00）

```
# 1. 切换扩展会话
session 3

# 2. 读取 VIN（确认当前值）
read_did F190

# 3. 安全访问（请求种子 + 发送密钥）
security 0x27

# 4. 通过 EOL 例程写入 VIN（需先完成安全访问）
routine FF00 1 4857595a54455354393030303030303031

# 5. 读取 VIN（验证写入结果）
read_did F190
```

> VIN 数据为 17 字节 ASCII 的十六进制编码，上例中 `4857595a54455354393030303030303031` 对应 `HWYZTEST900000001`。

##### 场景二：证书申请（RID 0xFF01 / 0xFF02 / 0xFF03）

```
# 1. 切换编程会话（证书 RID 仅在编程会话下可用）
session 2

# 2. 安全访问（请求种子 + 发送密钥）
security 0x27

# 3. 生成密钥对
routine FF01 1

# 4. 读取 CSR（DER 编码，响应中包含 CSR 数据）
routine FF02 1

# 5. 注入证书（将从 PKI 获取的证书以 DER 编码传入）
routine FF03 1 device.der
```

> 证书流程分三步独立调用，由测试端控制顺序：
> - `0xFF01` (GENERATE_KEY_PAIR)：SEC 服务生成密钥对
> - `0xFF02` (READ_CSR)：SEC 服务生成 CSR，响应中返回 DER 编码的 CSR 数据
> - `0xFF03` (INJECT_CERTIFICATE)：将 PKI 签发的证书注入设备
>
> 会话要求：必须在 **Programming Session (0x02)** 下执行，扩展会话下会返回 NRC `0x7F`。
>
> 失败时常见 NRC：`0x33`（安全访问未解锁）、`0x22`（SEC 服务不可用）、`0x72`（密钥生成/CSR 创建/证书注入失败）、`0x7F`（会话不正确）。

##### 场景三：售后 DTC 诊断

```
# 1. 读取支持的 DTC（默认会话即可）
read_dtc 0A

# 2. 按状态掩码读取 DTC
read_dtc 02 ff

# 3. 切换扩展会话
session 3

# 4. 安全访问（请求种子 + 发送密钥）
security 0x27

# 5. 清除所有 DTC（需安全访问）
clear_dtc ffffff

# 6. 验证 DTC 已清除
read_dtc 02 ff

# 7. 切换回默认会话
session 1
```

> 注意：DIAG 暂不支持 `0x19`（ReadDTCInformation）和 `0x14`（ClearDiagnosticInformation），会返回 NRC `0x11`。以上命令仅用于验证 NRC 响应。

#### 测试用例验证

```bash
# 运行 EOL 测试用例（VIN 写入）
dte run tests/fixtures/test_cases/eol_provisioning.yaml \
       --profile profiles.yaml \
       --profile-name diag_test

# 运行证书申请测试用例
dte run tests/fixtures/test_cases/cert_provisioning.yaml \
       --profile profiles.yaml \
       --profile-name diag_test

# 运行 DTC 测试用例（注意：DIAG 暂不支持 0x14/0x19，会返回 NRC 0x11）
dte run tests/fixtures/test_cases/aftersales_dtc.yaml \
       --profile profiles.yaml \
       --profile-name diag_test
```

## 与 DIAG 服务的兼容性矩阵

| UDS 服务 | SID | DTE 支持 | DIAG 支持 | 可对接 |
|----------|-----|----------|-----------|--------|
| DiagnosticSessionControl | 0x10 | ✅ | ✅ | ✅ |
| TesterPresent | 0x3E | ✅ | ✅ | ✅ |
| SecurityAccess | 0x27 | ✅ | ✅ | ✅ |
| ReadDataByIdentifier | 0x22 | ✅ | ✅ | ✅ |
| RoutineControl 0xFF00 (写入 VIN) | 0x31 | ✅ | ✅ | ✅ |
| RoutineControl 0xFF01 (生成密钥对) | 0x31 | ✅ | ✅ | ✅ |
| RoutineControl 0xFF02 (读取 CSR) | 0x31 | ✅ | ✅ | ✅ |
| RoutineControl 0xFF03 (注入证书) | 0x31 | ✅ | ✅ | ✅ |
| WriteDataByIdentifier | 0x2E | ✅ | ❌ | ❌ |
| ReadDTCInformation | 0x19 | ✅ | ❌ | ❌ |
| ClearDiagnosticInformation | 0x14 | ✅ | ❌ | ❌ |
| InputOutputControlByIdentifier | 0x2F | ✅ | ❌ | ❌ |

### RoutineControl 业务场景汇总

| RID | 业务场景 | 下游服务 | 会话要求 | 安全要求 | 交互命令示例 |
|-----|----------|----------|----------|----------|-------------|
| 0xFF00 | EOL 写入 VIN | PROV | Extended (0x03) | Level 0x27 | `routine FF00 1 <VIN_HEX>` |
| 0xFF01 | 生成密钥对 | SEC | Programming (0x02) | Level 0x27 | `routine FF01 1` |
| 0xFF02 | 读取 CSR | SEC | Programming (0x02) | Level 0x27 | `routine FF02 1` |
| 0xFF03 | 注入证书 | SEC | Programming (0x02) | Level 0x27 | `routine FF03 1 <CERT_HEX>` |

## 对接 DIAG 的标准流程

### EOL 写入 VIN 流程（RID 0xFF00）

```
DTE                                DIAG (TBOX)
 │                                   │
 │──── TCP connect :13400 ──────────►│
 │                                   │
 │──── Routing Activation (0x0005) ─►│
 │◄─── Routing Accept (0x0006) ──────│
 │                                   │
 │──── 0x10 0x03 (Extended) ────────►│
 │◄─── 0x50 0x03 ────────────────────│
 │                                   │
 │──── 0x27 0x01 (Request Seed) ────►│
 │◄─── 0x67 0x01 [seed] ─────────────│
 │                                   │
 │──── 0x27 0x02 [key] ─────────────►│
 │◄─── 0x67 0x02 ────────────────────│
 │                                   │
 │──── 0x31 0x01 0xFF00 [VIN] ──────►│
 │◄─── 0x71 0x01 0xFF00 ─────────────│  ← PROV 写入 VIN
 │                                   │
 │──── 0x22 0xF190 (Read VIN) ──────►│
 │◄─── 0x62 0xF190 [VIN] ────────────│
 │                                   │
 │  ... 每 5 秒内发 0x3E 保活 ...     │
```

### 证书申请流程（RID 0xFF01 / 0xFF02 / 0xFF03）

```
DTE                                DIAG (TBOX)           SEC
 │                                   │                    │
 │──── TCP connect :13400 ──────────►│                    │
 │                                   │                    │
 │──── Routing Activation (0x0005) ─►│                    │
 │◄─── Routing Accept (0x0006) ──────│                    │
 │                                   │                    │
 │──── 0x10 0x02 (Programming) ─────►│                    │
 │◄─── 0x50 0x02 ────────────────────│                    │
 │                                   │                    │
 │──── 0x27 0x01 (Request Seed) ────►│                    │
 │◄─── 0x67 0x01 [seed] ─────────────│                    │
 │                                   │                    │
 │──── 0x27 0x02 [key] ─────────────►│                    │
 │◄─── 0x67 0x02 ────────────────────│                    │
 │                                   │                    │
 │──── 0x31 0x01 0xFF01 ────────────►│                    │
 │                                   │── generate_key_pair►│
 │                                   │◄─ key_pair_ok ─────│
 │◄─── 0x71 0x01 0xFF01 ─────────────│                    │
 │                                   │                    │
 │──── 0x31 0x01 0xFF02 ────────────►│                    │
 │                                   │── get_csr ─────────►│
 │                                   │◄─ csr_der ─────────│
 │◄─── 0x71 0x01 0xFF02 [CSR] ───────│                    │
 │                                   │                    │
 │  (DTE 将 CSR 发送给 PKI 签发证书)  │                    │
 │                                   │                    │
 │──── 0x31 0x01 0xFF03 [cert] ─────►│                    │
 │                                   │── inject_cert ─────►│
 │                                   │◄─ injected ────────│
 │◄─── 0x71 0x01 0xFF03 ─────────────│                    │
 │                                   │                    │
 │  ... 每 5 秒内发 0x3E 保活 ...     │
```

> 证书流程由三个独立的 RoutineControl 调用组成，DTE 控制执行顺序。必须在 Programming Session (0x02) 下执行。
> `submit_csr()` 在 SEC 服务内部完成，不单独暴露为 UDS RID。

## 常见问题

### Q: 连接 DIAG 超时？
A: 检查以下项目：
- DIAG 服务是否已启动并监听 13400 端口
- 防火墙是否放行 TCP 13400
- `profiles.yaml` 中的 `target_ip` 是否正确

### Q: 所有 UDS 请求都返回 NRC 0x11 (serviceNotSupported)？
A: DoIP 寻址字节处理不一致。确认 DIAG 的 `doip_adapter.cpp` 中 `receive()` 剥离了 4 字节（source + target），`send()` 添加了 4 字节寻址。

### Q: SecurityAccess 失败，返回 NRC 0x12？
A: 确认 DTE 调用 `security_access(level=0x27)`，level 必须为 `0x27`，与 DIAG 支持的安全级别一致。

### Q: SecurityAccess 失败，返回 NRC 0x35 (invalidKey)？
A: 检查 DTE 的 `security_adapter` 配置。对接 DIAG 的 stub 实现时，任意 key 均可通过；对接正式 SEC 服务时，需配置正确的 key 计算逻辑。

### Q: 测试用例中用到 0x19/0x14/0x2F 会失败？
A: DIAG 暂不支持这些服务，会返回 NRC 0x11。测试用例中应避免使用，或设置 `expect.success: false` + `expect.nrc: 0x11`。

### Q: S3 会话超时？
A: DIAG 的 S3 超时为 5 秒。在扩展/编程会话下，需在 5 秒内发送 TesterPresent (0x3E)。DTE 的 `udsoncan` 会自动处理，但需确认 `ClientConfig` 中的 p2_star 设置正确。

### Q: 证书相关 RID 返回 NRC 0x7F (serviceNotSupportedInActiveSession)？
A: 证书 RID（0xFF01/0xFF02/0xFF03）必须在 Programming Session (0x02) 下执行。确认先发送 `session 2` 切换到编程会话，而非 `session 3`（扩展会话）。
