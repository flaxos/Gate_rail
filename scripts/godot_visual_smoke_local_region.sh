#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export GODOT_SMOKE_HEADLESS=0
export GATERAIL_SMOKE_REQUIRE_PIXELS=1

exec "${ROOT_DIR}/scripts/godot_smoke_local_region.sh"
