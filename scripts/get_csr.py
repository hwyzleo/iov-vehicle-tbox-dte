#!/usr/bin/env python3
"""Request a CSR from the TBOX and print it as base64 / PEM.

Flow (per docs/build-and-verify.md 证书申请流程):
  0x10 0x02  switch to programming session
  0x27 0x01/0x02  security access level 1 (DIAG 的证书 RID 校验 is_unlocked(0x01))
  0x31 0x01 0xFF01  generate key pair (skippable with --no-keygen)
  0x31 0x01 0xFF02  read CSR  -> response 0x71 0x01 0xFF02 [CSR DER]
  0x10 0x01  back to default session

Seed-Key: key = AES-128-ECB(shared_secret, seed)，与 SEC 的
SecService::compute_expected_key 一致。共享密钥需与设备上 provisioning 注入的
sec.seed_key.shared_secret 相同（32 个 hex 字符），通过 --shared-secret 或环境变量
TBOX_SEED_KEY_SECRET 提供。

Usage:
    export TBOX_SEED_KEY_SECRET=<32 hex chars>
    python scripts/get_csr.py --profile doip_orin.yaml --profile-name doip_orin
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dte.config.loader import load_config  # noqa: E402
from dte.transport.factory import create_transport  # noqa: E402
from dte.uds.client import TransportConnection, UDSClient  # noqa: E402
from dte.uds.security import AES128ECBAdapter  # noqa: E402

RID_GENERATE_KEY_PAIR = 0xFF01
RID_READ_CSR = 0xFF02

# DIAG 对证书类 RID 统一检查 level-1 解锁状态键 0x01
# （constants.h: UdsSecurityLevel::LEVEL_1 = 0x01）。
# requestSeed 用 0x01，sendKey 用 0x02。
SECURITY_LEVEL = 0x01

# Routine positive response header: SID(0x71) + controlType + RID(2 bytes)
ROUTINE_RESP_HEADER_LEN = 4


def _check(label: str, resp) -> None:
    if not resp.positive:
        nrc = f"0x{resp.nrc:02X}" if resp.nrc is not None else "unknown"
        raise SystemExit(f"[FAIL] {label}: NRC {nrc} (raw={resp.raw.hex()})")
    print(f"[ OK ] {label}: {resp.raw.hex()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch CSR from TBOX via UDS/DoIP")
    parser.add_argument("--profile", "-p", required=True, help="Transport profile YAML/JSON")
    parser.add_argument("--profile-name", "-n", default=None, help="Profile name in the file")
    parser.add_argument(
        "--out", "-o", default="csr.pem",
        help="Write CSR as PEM to this path (default: csr.pem)",
    )
    parser.add_argument(
        "--der-out", default=None,
        help="Optionally also write the raw DER bytes to this path",
    )
    parser.add_argument(
        "--no-keygen", action="store_true",
        help="Skip 0xFF01 (reuse the existing key pair on the device)",
    )
    parser.add_argument(
        "--shared-secret", default=None,
        help="Seed-Key AES-128 shared secret, 32 hex chars "
             "(defaults to $TBOX_SEED_KEY_SECRET)",
    )
    args = parser.parse_args()

    secret_hex = args.shared_secret or os.environ.get("TBOX_SEED_KEY_SECRET")
    if not secret_hex:
        raise SystemExit(
            "[FAIL] Seed-Key 共享密钥未提供。请设置 --shared-secret 或环境变量 "
            "TBOX_SEED_KEY_SECRET（32 hex 字符），且必须与设备上 "
            "sec.seed_key.shared_secret 一致。"
        )
    security_adapter = AES128ECBAdapter.from_hex(secret_hex)

    profiles = load_config(Path(args.profile))
    if not profiles:
        raise SystemExit(f"No profiles in {args.profile}")
    if args.profile_name:
        if args.profile_name not in profiles:
            raise SystemExit(
                f"Profile '{args.profile_name}' not found. "
                f"Available: {', '.join(profiles)}"
            )
        profile = profiles[args.profile_name]
    else:
        profile = next(iter(profiles.values()))

    transport = create_transport(profile)
    print(f"Connecting to {profile.doip.target_ip}:{profile.doip.tcp_port} ...")
    transport.connect()
    print("Connected.")

    conn = TransportConnection(transport)
    client = UDSClient(conn=conn, security_adapter=security_adapter)

    try:
        _check("session 2 (programming)", client.session_control(0x02))
        _check(
            f"security level 0x{SECURITY_LEVEL:02X}",
            client.security_access(SECURITY_LEVEL),
        )

        if not args.no_keygen:
            _check(
                "routine FF01 (generate key pair)",
                client.routine_control(RID_GENERATE_KEY_PAIR, 0x01),
            )

        resp = client.routine_control(RID_READ_CSR, 0x01)
        _check("routine FF02 (read CSR)", resp)

        csr_der = resp.raw[ROUTINE_RESP_HEADER_LEN:]
        if not csr_der:
            raise SystemExit("[FAIL] routine FF02 returned no CSR payload")

        b64 = base64.b64encode(csr_der).decode("ascii")
        pem = (
            "-----BEGIN CERTIFICATE REQUEST-----\n"
            + "\n".join(textwrap.wrap(b64, 64))
            + "\n-----END CERTIFICATE REQUEST-----\n"
        )

        print(f"\nCSR DER length: {len(csr_der)} bytes")
        print("\n===== CSR base64 (single line, for the PKI portal) =====")
        print(b64)
        print("\n===== CSR PEM =====")
        print(pem, end="")

        Path(args.out).write_text(pem)
        print(f"\nPEM written to {args.out}")
        if args.der_out:
            Path(args.der_out).write_bytes(csr_der)
            print(f"DER written to {args.der_out}")
        return 0
    finally:
        try:
            client.session_control(0x01)
        except Exception:
            pass
        transport.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    sys.exit(main())
