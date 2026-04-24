"""JSON-over-stdio bridge for future Stage 2 clients."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TextIO

from gaterail.commands import command_from_dict
from gaterail.simulation import TickSimulation
from gaterail.snapshot import SNAPSHOT_VERSION, render_snapshot


def _message_commands(message: dict[str, object]) -> list[dict[str, object]]:
    """Extract command objects from a bridge message."""

    if "commands" in message:
        commands = message["commands"]
        if not isinstance(commands, list):
            raise ValueError("commands must be a list")
        return [command for command in commands if isinstance(command, dict)]
    if "command" in message:
        command = message["command"]
        if not isinstance(command, dict):
            raise ValueError("command must be an object")
        return [command]
    if "type" in message:
        return [message]
    return []


def _message_ticks(message: dict[str, object]) -> int:
    """Extract the tick count from a bridge message."""

    ticks = int(message.get("ticks", 1))
    if ticks < 0:
        raise ValueError("ticks cannot be negative")
    return ticks


def handle_bridge_message(simulation: TickSimulation, message: dict[str, object]) -> dict[str, object]:
    """Apply one bridge message and return a render snapshot."""

    command_results: list[dict[str, object]] = []
    for command_data in _message_commands(message):
        command = command_from_dict(command_data)
        command_results.append(simulation.state.apply_command(command))

    ticks = _message_ticks(message)
    reports = simulation.run_ticks(ticks)
    snapshot = render_snapshot(simulation.state)
    snapshot["bridge"] = {
        "ok": True,
        "stepped_ticks": len(reports),
        "command_results": command_results,
    }
    return snapshot


def bridge_error(message: str) -> dict[str, object]:
    """Return a JSON-safe bridge error frame."""

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "bridge": {
            "ok": False,
            "error": message,
        },
    }


def iter_stdio_snapshots(simulation: TickSimulation, lines: Iterable[str]) -> Iterable[dict[str, object]]:
    """Yield bridge responses for newline-delimited JSON input."""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            message = json.loads(stripped)
            if not isinstance(message, dict):
                raise ValueError("bridge message must be a JSON object")
            yield handle_bridge_message(simulation, message)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            yield bridge_error(str(exc))


def run_stdio_bridge(
    simulation: TickSimulation,
    *,
    input_stream: TextIO,
    output_stream: TextIO,
) -> int:
    """Run the newline-delimited JSON bridge until input EOF."""

    for snapshot in iter_stdio_snapshots(simulation, input_stream):
        output_stream.write(json.dumps(snapshot, sort_keys=True, separators=(",", ":")))
        output_stream.write("\n")
        output_stream.flush()
    return 0
