"""Command-line interface for DTE."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.table import Table

from dte import __version__
from dte.config.loader import ConfigLoaderError, load_config
from dte.config.transport_profile import TransportProfile
from dte.engine.scenario import ScenarioEngine
from dte.model.test_case import TestCase
from dte.transport.factory import create_transport

console = Console()


def _load_test_case(path: Path) -> TestCase:
    """Load a test case from a JSON or YAML file.

    Args:
        path: Path to test case file.

    Returns:
        TestCase instance.

    Raises:
        click.ClickException: If file cannot be loaded.
    """
    path = Path(path)
    if not path.exists():
        raise click.ClickException(f"Test case file not found: {path}")

    suffix = path.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        elif suffix == ".json":
            with open(path) as f:
                data = json.load(f)
        else:
            raise click.ClickException(
                f"Unsupported file format: {suffix}. Use .yaml, .yml, or .json"
            )
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Failed to parse test case file: {e}") from e

    try:
        return TestCase.from_dict(data)
    except (KeyError, TypeError) as e:
        raise click.ClickException(f"Invalid test case format: {e}") from e


def _load_profile(config_path: Path, profile_name: str | None = None) -> TransportProfile:
    """Load a transport profile from a config file.

    Args:
        config_path: Path to configuration file.
        profile_name: Name of profile to load. If None, loads the first profile.

    Returns:
        TransportProfile instance.

    Raises:
        click.ClickException: If profile cannot be loaded.
    """
    try:
        profiles = load_config(config_path)
    except ConfigLoaderError as e:
        raise click.ClickException(str(e)) from e

    if not profiles:
        raise click.ClickException("No profiles found in configuration file")

    if profile_name:
        if profile_name not in profiles:
            available = ", ".join(profiles.keys())
            raise click.ClickException(
                f"Profile '{profile_name}' not found. Available: {available}"
            )
        return profiles[profile_name]

    return next(iter(profiles.values()))


def _print_report(record: Any, output_format: str) -> None:
    """Print test execution report.

    Args:
        record: SessionRecord from test execution.
        output_format: Output format ('text' or 'json').
    """
    if output_format == "json":
        click.echo(json.dumps(record.to_dict(), indent=2))
        return

    table = Table(title="Test Execution Results")
    table.add_column("Step", style="cyan")
    table.add_column("Verdict", style="bold")
    table.add_column("Duration", justify="right")

    for result in record.step_results:
        verdict_style = "green" if result.verdict == "pass" else "red"
        duration = f"{result.duration_ms:.1f}ms" if result.duration_ms else "N/A"
        table.add_row(
            result.step_id,
            f"[{verdict_style}]{result.verdict}[/{verdict_style}]",
            duration,
        )

    console.print(table)
    console.print(f"\nSession state: [bold]{record.state}[/]")


@click.group()
@click.version_option(version=__version__, prog_name="dte")
def main() -> None:
    """TBOX Diagnostic Tester Emulator (DTE) CLI."""
    pass


@main.command()
@click.argument("case_file", type=click.Path(exists=True))
@click.option(
    "--profile", "-p", required=True, type=click.Path(exists=True),
    help="Transport profile config file",
)
@click.option(
    "--profile-name", "-n", type=str, default=None,
    help="Profile name within config file",
)
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]),
    default="text", help="Output format",
)
def run(case_file: str, profile: str, profile_name: str | None, output: str) -> None:
    """Execute a test case.

    CASE_FILE is the path to the test case file (JSON or YAML).
    """
    console.print("[bold green]Running test case...[/]")

    test_case = _load_test_case(Path(case_file))
    transport_profile = _load_profile(Path(profile), profile_name)

    console.print(f"Test case: {test_case.name} ({test_case.id})")
    console.print(f"Profile: {transport_profile.name} ({transport_profile.transport_type.value})")

    engine = ScenarioEngine()
    try:
        record = engine.execute_test_case(test_case, transport_profile)
        _print_report(record, output)
        sys.exit(0 if record.passed else 1)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@main.command()
@click.option(
    "--profile", "-p", required=True, type=click.Path(exists=True),
    help="Transport profile config file",
)
@click.option(
    "--profile-name", "-n", type=str, default=None,
    help="Profile name within config file",
)
def connect(profile: str, profile_name: str | None) -> None:
    """Start interactive diagnostic session.

    Establishes a connection using the specified transport profile
    and enters interactive mode for sending UDS commands.
    """
    transport_profile = _load_profile(Path(profile), profile_name)

    console.print(f"[bold green]Connecting via {transport_profile.transport_type.value}...[/]")
    console.print(f"Profile: {transport_profile.name}")

    transport = create_transport(transport_profile)
    try:
        transport.connect()
        console.print("[bold green]Connected![/]")
        console.print("Type 'help' for available commands, 'quit' to exit.\n")

        _interactive_loop(transport)
    except Exception as e:
        console.print(f"[bold red]Connection error:[/] {e}")
        sys.exit(1)
    finally:
        transport.disconnect()
        console.print("[yellow]Disconnected.[/]")


def _interactive_loop(transport: Any) -> None:
    """Run the interactive command loop.

    Args:
        transport: Connected transport instance.
    """
    from dte.uds.client import TransportConnection, UDSClient

    conn = TransportConnection(transport)
    client = UDSClient(conn=conn)

    while True:
        try:
            cmd = console.input("[bold cyan]dte>[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Exiting...[/]")
            break

        if not cmd:
            continue

        if cmd in ("quit", "exit", "q"):
            break

        if cmd == "help":
            _print_help()
            continue

        if cmd == "status":
            console.print(f"Connected: {transport.is_connected}")
            console.print(f"Transport: {transport.profile.transport_type.value}")
            continue

        _dispatch_interactive(client, cmd)


def _print_help() -> None:
    """Print interactive mode help."""
    help_text = """Available commands:
  help              Show this help
  status            Show connection status
  session <type>    Switch session (1=default, 2=programming, 3=extended)
  read_did <hex>    Read DID (e.g., read_did F190)
  write_did <hex> <hex_data>  Write DID
  security <level>  Security access
  routine <id> <type>  Routine control
  read_dtc <mask>   Read DTCs
  clear_dtc         Clear all DTCs
  quit/exit/q       Exit interactive mode"""
    console.print(help_text)


def _dispatch_interactive(client: Any, cmd: str) -> None:
    """Dispatch an interactive command.

    Args:
        client: UDSClient instance.
        cmd: Command string.
    """
    parts = cmd.split()
    command = parts[0].lower()

    try:
        if command == "session":
            if len(parts) < 2:
                console.print("[red]Usage: session <type>[/]")
                return
            session_type = int(parts[1], 0)
            response = client.session_control(session_type)
            console.print(f"Response: {response.raw.hex()}")

        elif command == "read_did":
            if len(parts) < 2:
                console.print("[red]Usage: read_did <hex_did>[/]")
                return
            did = int(parts[1], 16)
            response = client.read_did(did)
            console.print(f"Response: {response.raw.hex()}")

        elif command == "write_did":
            if len(parts) < 3:
                console.print("[red]Usage: write_did <hex_did> <hex_data>[/]")
                return
            did = int(parts[1], 16)
            data = bytes.fromhex(parts[2])
            response = client.write_did(did, data)
            console.print(f"Response: {response.raw.hex()}")

        elif command == "security":
            if len(parts) < 2:
                console.print("[red]Usage: security <level>[/]")
                return
            level = int(parts[1], 0)
            response = client.security_access(level)
            console.print(f"Response: {response.raw.hex()}")

        elif command == "routine":
            if len(parts) < 3:
                console.print("[red]Usage: routine <id> <type>[/]")
                return
            routine_id = int(parts[1], 16)
            control_type = int(parts[2], 0)
            response = client.routine_control(routine_id, control_type)
            console.print(f"Response: {response.raw.hex()}")

        elif command == "read_dtc":
            mask = int(parts[1], 16) if len(parts) > 1 else 0xFF
            response = client.read_dtc(mask)
            console.print(f"Response: {response.raw.hex()}")

        elif command == "clear_dtc":
            response = client.clear_dtc()
            console.print(f"Response: {response.raw.hex()}")

        else:
            console.print(
                f"[red]Unknown command: {command}. Type 'help' for commands.[/]"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@main.command()
@click.argument("profile_file", type=click.Path(exists=True))
@click.option("--name", "-n", type=str, default=None, help="Profile name to validate")
def validate(profile_file: str, name: str | None) -> None:
    """Validate a transport profile configuration.

    PROFILE_FILE is the path to the transport profile config file.
    """
    console.print("[bold]Validating transport profile...[/]")

    try:
        profiles = load_config(Path(profile_file))
    except ConfigLoaderError as e:
        console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)

    if not profiles:
        console.print("[bold red]Error:[/] No profiles found in configuration file")
        sys.exit(1)

    if name:
        if name not in profiles:
            available = ", ".join(profiles.keys())
            console.print(f"[bold red]Error:[/] Profile '{name}' not found. Available: {available}")
            sys.exit(1)
        profiles_to_validate = {name: profiles[name]}
    else:
        profiles_to_validate = profiles

    all_valid = True
    for profile_name, profile in profiles_to_validate.items():
        errors = profile.validate()
        if errors:
            all_valid = False
            console.print(f"\n[bold red]Profile '{profile_name}' has errors:[/]")
            for error in errors:
                console.print(f"  - {error}")
        else:
            console.print(f"\n[bold green]Profile '{profile_name}' is valid[/]")
            console.print(f"  Transport: {profile.transport_type.value}")
            if profile.transport_type.value == "doip":
                console.print(f"  Target: {profile.doip.target_ip}:{profile.doip.tcp_port}")
            elif profile.transport_type.value == "can":
                console.print(f"  Channel: {profile.can.channel} ({profile.can.interface})")

    if all_valid:
        console.print("\n[bold green]All profiles are valid![/]")
        sys.exit(0)
    else:
        console.print("\n[bold red]Validation failed.[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
