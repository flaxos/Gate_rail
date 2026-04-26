# GateRail

GateRail is a simulation-first game project for logistics and world-building about **trains, wormholes, frontier development, and interplanetary supply chains**.

The long-term game fantasy combines three angles:
- railroad tycoon across impossible distances,
- industrial supply-chain optimizer,
- frontier builder growing worlds from outposts into major civil and industrial hubs.

The current repository focus is the Python backend plus the first Godot 2D client scaffold. The backend remains authoritative and is tested through terminal and JSON-over-stdio workflows; Godot is the Stage 2 view/input layer.

## Product direction

GateRail is built around these assumptions:
- trains are the dominant logistics layer for bulk cargo and mass transit,
- wormholes are powerful but energy-hungry infrastructure,
- worlds progress through development tiers,
- expansion depends on building stable interdependent supply chains,
- the backend product surface stays CLI/stdio-first,
- the Godot client talks to the backend through the documented JSON bridge.

This is now entering the first visual-client phase, but remains systems-first.

## Design goals

- Keep the simulation deterministic and testable.
- Make the game playable from terminal commands as early as possible.
- Use data and rules that can survive either a future custom engine path or a frontend client layered on top.
- Favor a small, proven core loop over broad but shallow feature lists.

## Long-term staging

Stage 1 is the current Python simulation: no graphics, with cargo demand, train schedules, gate slots, colony stockpiles, income, costs, and monthly text tables.

Stage 2 is the Godot 2D prototype: tile-based rail presentation, simple moving trains, cargo counters, wormhole gates, route UI, gate schedule UI, and staged construction controls.

Stage 3 is the proper game expansion: more worlds, contracts, corporate finance, rival operators, tech tree, modular stations, and advanced rail types.

## Core gameplay loop

The intended loop is:

1. Establish or unlock a world.
2. Build enough power, freight, and storage capacity to stabilize it.
3. Lay rail and station infrastructure between extraction, processing, population, and gate hubs.
4. Deliver the goods required to promote the world to a higher development tier.
5. Specialize the world into useful exports such as mining, food, refining, manufacturing, recycling, or research.
6. Connect it to the wider network with rail, space lanes, and eventually wormhole gates.
7. Use the stronger network to bootstrap the next world.

## Recommended simulation model

The backend should evolve through four explicit layers:
- `strategic`: worlds, tiers, specializations, demand, stability
- `economic`: resources, recipes, storage, deficits, surpluses
- `transport`: tracks, stations, trains, routing, congestion
- `gate`: wormhole links, activation, throughput, power cost

The live game feel can be real-time, but the backend should run on fixed ticks so behavior stays deterministic and easy to test.

## First playable target

The first true prototype should answer one question:

**Can the player bootstrap a frontier world into a self-sustaining industrial colony by building rail, assigning trains, and using one costly wormhole hub intelligently?**

That is the current MVP target.

## Documentation map

- [DESIGN_NOTES.md](DESIGN_NOTES.md): design principles and simulation boundaries
- [GAME_VISION.md](GAME_VISION.md): canonical concept brief and gameplay framing
- [PHASE2_PLAN.md](PHASE2_PLAN.md): Godot client and Stage 2 sprint plan
- [PHASE2_UI_WIREFRAME.md](PHASE2_UI_WIREFRAME.md): implementation summary from the Claude Design handoff
- [SPRINTS.md](SPRINTS.md): sprint-by-sprint development plan
- [docs/construction_rules.md](docs/construction_rules.md): authoritative local construction, train, and route-creation rules

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you are running tests:

```bash
pip install -e .[dev]
```

## Current commands

List the built-in playtest scenarios:

```bash
gaterail --list-scenarios
```

Inspect the current default Sprint 8 playtest setup without advancing time:

```bash
gaterail --inspect --report schedules,stockpiles
```

Run the fixed-tick Sprint 8 playability scenario after installing the package:

```bash
gaterail --ticks 30
```

Run it directly from a source checkout without installing:

```bash
PYTHONPATH=src python3 -m gaterail.main --ticks 30
```

Filter reports during focused playtests:

```bash
gaterail --ticks 30 --report traffic,finance
```

Save and resume a deterministic playtest:

```bash
gaterail --ticks 15 --save saves/playtest.json
gaterail --load saves/playtest.json --ticks 15 --report traffic,finance,schedules
```

Run the Stage 2 JSON bridge contract from a source checkout:

```bash
printf '{"ticks":1}\n' | PYTHONPATH=src python3 -m gaterail.main --stdio
```

Send a player command through the bridge:

```bash
printf '{"commands":[{"type":"SetScheduleEnabled","schedule_id":"core_food_service","enabled":false}],"ticks":1}\n' \
  | PYTHONPATH=src python3 -m gaterail.main --stdio
```

Open the Godot 4 client scaffold:

```bash
godot --path godot
```

The Godot scaffold has two scenes that share the `GateRailBridge` autoload:

- `scenes/main.tscn` (Galaxy Map) — draws the fixture immediately, then requests a live `{"ticks":0}` snapshot from the Python stdio bridge and redraws when the backend responds. Exposes bridge status, schedules, finance, contracts, one-shot dispatch, pending-order cancellation, auto-run, map entity inspection, placeholder SVG assets, and an alert/status strip for command history, bridge errors, disruptions, and congestion.
- `scenes/local_region.tscn` (Local Region Construction) — drilled into from the galaxy map by selecting a world and pressing **View Local Region** in the inspector. Renders the topbar / left tool rail / center canvas / right HUD / bottom status bar from the Claude Design handoff archived at [`docs/design_handoff/local_region_construction/`](docs/design_handoff/local_region_construction/). Node, gate-hub, same-world rail, train purchase, and first route-schedule creation use backend-owned preview/validation before commit; the right HUD Build Planner shows preview context and confirm/cancel actions. Built node layout metadata persists through snapshots/save-load. The **Galaxy Map** button returns to `main.tscn`.

Run the test suite:

```bash
pytest
```

The codebase now contains the full Sprint 9 objectives layer plus the Stage 2 bridge contract: cargo-delivery, frontier-support, and gate-recovery contracts; reputation; stable render snapshots; Python-level player commands; and a JSON-over-stdio mode for a future Godot subprocess. The fixed-tick backend is now the single source of truth ahead of the Stage 2 Godot 2D port.
