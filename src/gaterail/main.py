"""Main entry point for GateRail."""

from gaterail.cli import run_cli


def main() -> int:
    """Run the GateRail command-line interface."""
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
