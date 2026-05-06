#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${ROOT_DIR}/godot"
SMOKE_HOME="${TMPDIR:-/tmp}/gaterail-godot-smoke"
SNAPSHOT_PATH="${SMOKE_HOME}/tutorial_local_logistics_snapshot.json"

if [[ -z "${GODOT_BIN:-}" ]]; then
  if command -v godot4 >/dev/null 2>&1; then
    GODOT_BIN="$(command -v godot4)"
  elif command -v godot >/dev/null 2>&1; then
    GODOT_BIN="$(command -v godot)"
  else
    echo "Godot binary not found. Set GODOT_BIN=/path/to/godot." >&2
    exit 127
  fi
fi

mkdir -p \
  "${SMOKE_HOME}/home" \
  "${SMOKE_HOME}/data" \
  "${SMOKE_HOME}/config" \
  "${SMOKE_HOME}/cache"

PYTHONPATH="${ROOT_DIR}/src" python3 - <<'PY' > "${SNAPSHOT_PATH}"
import json

from gaterail.bridge import handle_bridge_message
from gaterail.simulation import TickSimulation

simulation = TickSimulation.from_scenario("tutorial_local_logistics")
snapshot = handle_bridge_message(simulation, {"ticks": 0})
print(json.dumps(snapshot, separators=(",", ":")))
PY

GODOT_ARGS=()
if [[ "${GODOT_SMOKE_HEADLESS:-1}" != "0" ]]; then
  if [[ "${GATERAIL_SMOKE_REQUIRE_PIXELS:-0}" == "1" ]]; then
    echo "Pixel smoke requires visual mode. Run with GODOT_SMOKE_HEADLESS=0 on a working display server." >&2
    exit 125
  fi
  GODOT_ARGS+=(--headless)
else
  if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    echo "Visual smoke requires a working X11 or Wayland display. Use default headless mode in CI." >&2
    exit 125
  fi
  if [[ -n "${DISPLAY:-}" ]] && command -v xdpyinfo >/dev/null 2>&1; then
    if ! xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
      echo "Visual smoke cannot open DISPLAY=${DISPLAY}. Use a real desktop session or run the default headless smoke." >&2
      exit 125
    fi
  fi
fi

HOME="${SMOKE_HOME}/home" \
XDG_DATA_HOME="${SMOKE_HOME}/data" \
XDG_CONFIG_HOME="${SMOKE_HOME}/config" \
XDG_CACHE_HOME="${SMOKE_HOME}/cache" \
GATERAIL_SMOKE_SNAPSHOT="${SNAPSHOT_PATH}" \
GATERAIL_LOCAL_REGION_SMOKE=1 \
timeout "${GODOT_SMOKE_TIMEOUT:-15s}" \
"${GODOT_BIN}" "${GODOT_ARGS[@]}" --path "${PROJECT_DIR}" --script res://scripts/local_region_scene_smoke.gd
