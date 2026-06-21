"""Command-line interface for DTE."""
from __future__ import annotations

import click
from rich.console import Console

from dte import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="dte")
def main() -> None:
    """TBOX Diagnostic Tester Emulator (DTE) CLI."""
    pass


@main.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
def run(config: str | None) -> None:
    """Run diagnostic session."""
    console.print("[bold green]Starting DTE session...[/]")
    if config:
        console.print(f"Using config: {config}")
    else:
        console.print("No config specified, using defaults")


@main.command()
def version() -> None:
    """Show version information."""
    console.print(f"DTE version: {__version__}")


if __name__ == "__main__":
    main()
