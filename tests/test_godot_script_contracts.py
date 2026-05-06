"""Static contract checks for Godot scripts."""

from __future__ import annotations

from pathlib import Path
import re


def test_godot_scripts_do_not_call_nonexistent_bool_constructor() -> None:
    """Godot 4 GDScript has no bool() constructor."""

    script_root = Path("godot/scripts")
    offenders: list[str] = []
    for path in sorted(script_root.glob("*.gd")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "bool(" in line:
                offenders.append(f"{path}:{line_number}: {line.strip()}")

    assert offenders == []


def test_godot_scripts_do_not_infer_variant_from_min_max() -> None:
    """Godot treats Variant inference warnings as parse errors in this project."""

    script_root = Path("godot/scripts")
    offenders: list[str] = []
    pattern = re.compile(r"\bvar\s+\w+\s*:=\s*(?:max|min)\s*\(")
    for path in sorted(script_root.glob("*.gd")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{path}:{line_number}: {line.strip()}")

    assert offenders == []


def test_local_region_smoke_script_loads_scene_headlessly() -> None:
    """Goal 1 requires a repeatable smoke command for the Local Region scene."""

    script = Path("scripts/godot_smoke_local_region.sh")
    text = script.read_text(encoding="utf-8")
    visual_script = Path("scripts/godot_visual_smoke_local_region.sh")
    visual_text = visual_script.read_text(encoding="utf-8")

    assert script.exists()
    assert "--headless" in text
    assert "local_region_scene_smoke.gd" in text
    assert "tutorial_local_logistics" in text
    assert "GATERAIL_SMOKE_SNAPSHOT" in text
    assert "GATERAIL_LOCAL_REGION_SMOKE=1" in text
    assert "XDG_DATA_HOME" in text
    assert "GODOT_BIN" in text
    assert "GODOT_SMOKE_HEADLESS" in text
    assert "GODOT_ARGS" in text
    assert "Pixel smoke requires visual mode" in text
    assert "xdpyinfo" in text
    assert "Visual smoke cannot open DISPLAY" in text
    assert visual_script.exists()
    assert "GODOT_SMOKE_HEADLESS=0" in visual_text
    assert "GATERAIL_SMOKE_REQUIRE_PIXELS=1" in visual_text
    assert "godot_smoke_local_region.sh" in visual_text

    smoke_runner = Path("godot/scripts/local_region_scene_smoke.gd").read_text(encoding="utf-8")
    assert "res://scenes/local_region.tscn" in smoke_runner
    assert "SubViewport.new()" in smoke_runner
    assert "render_target_update_mode" in smoke_runner
    assert 'nav.set("selected_world_id", "atlas")' in smoke_runner
    assert 'scene.get("_world_operational_entities")' in smoke_runner
    assert "local region operational entities are blank" in smoke_runner
    assert 'grid.get("kind", "")' in smoke_runner
    assert 'scene.get("_canvas_panel")' in smoke_runner
    assert "local region canvas panel is missing" in smoke_runner
    assert 'scene.call("_operational_entity_position", entity)' in smoke_runner
    assert "local region operational entities project outside the canvas" in smoke_runner
    assert "_count_visible_controls(scene)" in smoke_runner
    assert "render_viewport.get_texture()" in smoke_runner
    assert "texture.get_image()" in smoke_runner
    assert "local region viewport rendered blank pixels" in smoke_runner


def test_local_region_guards_nullable_facility_storage_override() -> None:
    """Facility snapshots may send null storage overrides when no storage bay exists."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert 'facility.get("storage_capacity_override", 0)' in script
    assert "typeof(storage_value) in [TYPE_INT, TYPE_FLOAT]" in script
    assert 'int(facility.get("storage_capacity_override", 0))' not in script


def test_local_region_prefers_cached_live_snapshot_before_fixture() -> None:
    """Drilling into new scenario worlds must not overwrite live state with the fixture."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    cached_index = script.find("GateRailBridge.last_snapshot")
    fixture_index = script.find("GateRailBridge.load_fixture_snapshot")
    assert cached_index != -1
    assert fixture_index != -1
    assert cached_index < fixture_index


def test_local_region_smoke_does_not_request_live_bridge_snapshot() -> None:
    """The visual smoke must not be overwritten by a running/default bridge snapshot."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert 'OS.get_environment("GATERAIL_LOCAL_REGION_SMOKE") != "1"' in script
    assert "GateRailBridge.request_snapshot()" in script


def test_local_region_recovers_stale_world_to_operational_area() -> None:
    """A stale SceneNav world must not leave the local canvas blank on live snapshots."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert "func _select_snapshot_world" in script
    assert "func _world_has_operational_area" in script
    assert "_select_snapshot_world(worlds, operational_areas)" in script
    assert "requested_world_is_valid" in script


def test_local_region_build_tools_use_local_grid_placement_commands() -> None:
    """Local build tools should validate and commit through backend-owned grid commands."""

    script = Path("godot/scripts/local_region.gd").read_text(encoding="utf-8")

    assert "func _request_local_entity_preview" in script
    assert "func _local_track_path_cells_between" in script
    assert '"type": "local.validate_placement"' in script
    assert '"local.place_entity"' in script
    assert '"entity_type": _local_entity_type_for_node_kind(kind)' in script
    assert '"entity_type": "track_segment"' in script
    assert 'command["path_cells"] = path_cells' in script
    assert 'entity.get("path_cells", [])' in script
    assert 'entity.get("rail_diagnostics")' in script
    assert 'rail_diagnostics.get("signal_ids"' in script
    assert 'rail_diagnostics.get("blocked_events"' in script
    assert "func _request_local_signal_preview" in script
    assert "func _local_switches_for_link" in script
    assert '"type": "local.validate_signal"' in script
    assert '"local.place_signal"' in script
    assert '"type": "local.set_switch_route"' in script


def test_ui_theme_autoload_exposes_design_tokens() -> None:
    """UITheme must export the tokens main.gd / local_region.gd depend on."""

    theme = Path("godot/scripts/ui_theme.gd").read_text(encoding="utf-8")
    required_tokens = [
        "BG_0",
        "BG_1",
        "BG_2",
        "INK_0",
        "INK_1",
        "INK_3",
        "ACCENT",
        "GATE",
        "GOOD",
        "WARN",
        "BAD",
        "RAIL",
    ]
    for token in required_tokens:
        assert f"const {token}" in theme, f"UITheme missing token {token}"

    required_helpers = [
        "func panel_style",
        "func pill_style",
        "func alert_chip_style",
        "func sched_row_style",
        "func cargo_dot_color",
        "func style_label_caption",
        "func style_label_value",
        "func style_label_mono",
    ]
    for helper in required_helpers:
        assert helper in theme, f"UITheme missing helper {helper}"


def test_ui_theme_is_registered_as_autoload() -> None:
    project = Path("godot/project.godot").read_text(encoding="utf-8")
    assert 'UITheme="*res://scripts/ui_theme.gd"' in project


def test_main_gd_routes_panels_through_ui_theme() -> None:
    """High-traffic panels and the alert chip must consume UITheme, not hardcoded literals."""

    main = Path("godot/scripts/main.gd").read_text(encoding="utf-8")

    expected_calls = [
        "RenderingServer.set_default_clear_color(UITheme.BG_0)",
        "UITheme.panel_style(\"hud\")",
        "UITheme.panel_style(\"alert\")",
        "UITheme.panel_style(\"inspector\")",
        "UITheme.panel_style(\"tutorial\")",
        "UITheme.alert_chip_style(kind)",
        "UITheme.sched_row_style",
    ]
    for call in expected_calls:
        assert call in main, f"main.gd should route through {call}"
