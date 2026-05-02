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
