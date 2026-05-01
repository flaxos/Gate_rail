"""JSON-over-stdio bridge for future Stage 2 clients."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TextIO

from gaterail.commands import command_from_dict
from gaterail.persistence import load_simulation, save_simulation
from gaterail.simulation import TickSimulation
from gaterail.snapshot import SNAPSHOT_VERSION, render_snapshot


def _message_commands(message: dict[str, object]) -> list[dict[str, object]]:
    """Extract command objects from a bridge message."""

    if "commands" in message:
        commands = message["commands"]
        if not isinstance(commands, list):
            raise ValueError("commands must be a list")
        parsed: list[dict[str, object]] = []
        for index, command in enumerate(commands):
            if not isinstance(command, dict):
                raise ValueError(f"commands[{index}] must be an object")
            parsed.append(command)
        return parsed
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


def _message_path(message: dict[str, object], key: str) -> str | None:
    """Extract a save/load path from either a direct key or object payload."""

    value: object
    if f"{key}_path" in message:
        value = message[f"{key}_path"]
    elif key in message:
        value = message[key]
        if isinstance(value, dict):
            value = value.get("path")
    else:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}_path must be a non-empty string")
    return value


def _message_scenario(message: dict[str, object]) -> str | None:
    """Extract an optional built-in scenario reset request."""

    if "scenario" not in message:
        return None
    scenario = message["scenario"]
    if not isinstance(scenario, str) or not scenario.strip():
        raise ValueError("scenario must be a non-empty string")
    return scenario.strip()


def _replace_simulation(target: TickSimulation, source: TickSimulation) -> None:
    """Replace the live simulation in-place so bridge callers keep their handle."""

    target.state = source.state
    target.status = source.status
    target.reports = list(source.reports)
    target.monthly_reports = list(source.monthly_reports)


def handle_bridge_message(simulation: TickSimulation, message: dict[str, object]) -> dict[str, object]:
    """Apply one bridge message and return a render snapshot."""

    loaded_path = _message_path(message, "load")
    save_path = _message_path(message, "save")
    loaded_scenario = _message_scenario(message)
    if loaded_path is not None and loaded_scenario is not None:
        raise ValueError("bridge message cannot load a save file and scenario in the same frame")
    if loaded_path is not None:
        _replace_simulation(simulation, load_simulation(loaded_path))
    elif loaded_scenario is not None:
        _replace_simulation(simulation, TickSimulation.from_scenario(loaded_scenario))

    command_results: list[dict[str, object]] = []
    for command_data in _message_commands(message):
        command = command_from_dict(command_data)
        command_results.append(simulation.state.apply_command(command))

    ticks = _message_ticks(message)
    reports = simulation.run_ticks(ticks)
    if save_path is not None:
        save_simulation(simulation, save_path)
    snapshot = render_snapshot(simulation.state)
    bridge: dict[str, object] = {
        "ok": True,
        "stepped_ticks": len(reports),
        "command_results": command_results,
    }
    if loaded_path is not None:
        bridge["loaded_path"] = loaded_path
    if loaded_scenario is not None:
        bridge["loaded_scenario"] = loaded_scenario
    if save_path is not None:
        bridge["saved_path"] = save_path
    snapshot["bridge"] = bridge
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
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
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
