"""Static contract checks for Godot scripts."""

from __future__ import annotations

from pathlib import Path


def test_godot_scripts_do_not_call_nonexistent_bool_constructor() -> None:
    """Godot 4 GDScript has no bool() constructor."""

    script_root = Path("godot/scripts")
    offenders: list[str] = []
    for path in sorted(script_root.glob("*.gd")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "bool(" in line:
                offenders.append(f"{path}:{line_number}: {line.strip()}")

    assert offenders == []


def test_local_region_prefers_cached_live_snapshot_before_fixture() -> None:
    """Drilling into new scenario worlds must not overwrite live state with the fixture."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    cached_index = script.find("GateRailBridge.last_snapshot")
    fixture_index = script.find("GateRailBridge.load_fixture_snapshot")
    assert cached_index != -1
    assert fixture_index != -1
    assert cached_index < fixture_index


def test_local_region_does_not_replace_requested_world_when_snapshot_lacks_it() -> None:
    """A fixture without the requested world should not permanently redirect to core."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert "_selected_world.is_empty() and _world_id.is_empty() and not worlds.is_empty()" in script
