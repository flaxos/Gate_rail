# Placeholder Asset Usage

These SVGs are temporary MVP art for the Godot Stage 2 client. They are intentionally simple and replaceable.

## Wired In `godot/scripts/main.gd`

- Worlds:
  - `world_core.svg` for core worlds and tier 3+ worlds.
  - `world_frontier.svg` for standard frontier worlds.
  - `world_outpost.svg` for survey/outpost worlds such as Ashfall.

- Nodes:
  - `node_depot.svg` for `depot`.
  - `node_settlement.svg` for `settlement`.
  - `node_extractor.svg` for `extractor`.
  - `node_industry.svg` for `industry`.
  - `node_gate_hub.svg` for `gate_hub`.

- Trains:
  - `train_freight.svg` for active/idle freight trains.
  - `train_blocked.svg` for blocked trains or trains with a blocked reason.
  - `train_passenger.svg` is reserved for passenger work later.

- Cargo and rows:
  - Cargo icons render in schedule rows when the cargo type has a matching SVG.
  - Unknown cargo falls back to `ui_dispatch.svg`.

- Buttons:
  - `ui_refresh.svg` for live snapshot refresh.
  - `ui_step.svg` for single-tick stepping.
  - `ui_schedule_on.svg` and `ui_schedule_off.svg` for schedule toggles.
  - `ui_dispatch.svg` for one-shot dispatch.
  - `ui_cancel.svg` for canceling pending orders.

- Panels:
  - `ui_contract.svg` prefixes contract rows.
  - `ui_cash.svg`, `ui_reputation.svg`, `ui_warning.svg`, `ui_play.svg`, and `ui_pause.svg` are available for the next HUD/status pass.

## Fallback Rules

The scene keeps shape/color fallbacks. Missing or failed SVG imports should not break rendering:

- missing world asset: draw a world circle and outline,
- missing node asset: draw a colored node dot,
- missing train asset: draw a small train rectangle,
- missing UI icon: render text-only button.

## Replacement Rules

When replacing these placeholders:

- keep filenames stable unless the scene mapping is updated in the same change,
- preserve transparent backgrounds,
- keep icons readable at 22-32 px,
- avoid embedding protected IP references,
- prefer SVG for source control readability.
