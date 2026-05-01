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
- expansion depends on building stable interdependent supply chains from raw extraction through advanced manufacturing,
- power plants and gates eventually depend on mined, refined, and manufactured inputs,
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

Stage 3 is the proper game expansion: elemental resource chains, space extraction, outpost construction, power-plant and gate-energy economies, more worlds, contracts, corporate finance, rival operators, tech tree, facility/station automation, advanced rail types, and eventually 3D facility presentation after the core systems are proven.

## Core gameplay loop

The intended loop is:

1. Establish or unlock a world.
2. Build enough power, freight, and storage capacity to stabilize it.
3. Lay rail and station infrastructure between extraction, processing, population, and gate hubs.
4. Prospect local or remote deposits and move raw resources into sorting, smelting, refining, and manufacturing chains.
5. Deliver the goods required to promote the world to a higher development tier.
6. Specialize the world into useful exports such as mining, food, refining, manufacturing, recycling, power, gate components, or research.
7. Connect it to the wider network with rail, collection stations, mining missions, space lanes, and eventually wormhole gates.
8. Use the stronger network to bootstrap the next world.

## Recommended simulation model

The backend should evolve through four explicit layers:
- `strategic`: worlds, tiers, specializations, demand, stability
- `economic`: resources, recipes, storage, deficits, surpluses
- `transport`: tracks, stations, trains, routing, congestion
- `gate`: wormhole links, activation, throughput, power cost
- `facility`: station/depot/hub internals such as platforms, loaders, unloaders, buffers, factory blocks, and internal cargo ports
- `space_extraction`: remote sites, mining missions, orbital yards, collection stations, and outpost construction

The live game feel can be real-time, but the backend should run on fixed ticks so behavior stays deterministic and easy to test.

## First playable target

The first true prototype should answer one question:

**Can the player bootstrap a frontier world into a self-sustaining industrial colony by building rail, extracting and refining raw resources, manufacturing key parts, powering local industry and gates, and using one costly wormhole hub intelligently?**

That is the current MVP target.

## Documentation map

- [DESIGN_NOTES.md](DESIGN_NOTES.md): design principles and simulation boundaries
- [GAME_VISION.md](GAME_VISION.md): canonical concept brief and gameplay framing
- [PHASE2_PLAN.md](PHASE2_PLAN.md): Godot client and Stage 2 sprint plan
- [PHASE2_UI_WIREFRAME.md](PHASE2_UI_WIREFRAME.md): implementation summary from the Claude Design handoff
- [SPRINTS.md](SPRINTS.md): sprint-by-sprint development plan
- [docs/construction_rules.md](docs/construction_rules.md): authoritative local construction, train, and route-creation rules
- [docs/facility_layer_plan.md](docs/facility_layer_plan.md): planned station/depot/hub automation layer before any 3D facility view
- [docs/resource_industry_plan.md](docs/resource_industry_plan.md): elemental resource, refining, manufacturing, power, space extraction, and outpost roadmap
- [docs/rail_network_plan.md](docs/rail_network_plan.md): planned curved alignments, branches, signals, vacuum tubes, consists, and cargo wagons

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

Inspect the current default playtest setup without advancing time:

```bash
gaterail --inspect --report schedules,stockpiles
```

Run the current default fixed-tick playtest scenario after installing the package:

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

Start from the Sprint 26 test presets:

```bash
gaterail --scenario early_build --inspect --report schedules,stockpiles
gaterail --scenario industrial_expansion --ticks 20 --report traffic,resources,power,schedules
```

Start from the six-world tutorial ring:

```bash
gaterail --scenario tutorial_six_worlds --inspect --report schedules,stockpiles
gaterail --load saves/tutorial_six_worlds.json --ticks 20 --report schedules,finance
```

In Godot, load `tutorial_six_worlds` or `saves/tutorial_six_worlds.json`. The tutorial schedules start disabled for manual playtesting: click a train on the galaxy map, click a pickup node, click a dropoff node, then queue the one-shot dispatch. After the manual route works, enable or create schedules to automate the supply route. The Tutorial Loop panel is driven by the backend `tutorial` snapshot payload.

Run the closed mining-to-settlement payoff loop through stdio:

```bash
printf '{"scenario":"mining_loop","commands":[{"type":"DispatchMiningMission","mission_id":"mission_loop","site_id":"site_brink_belt","launch_node_id":"frontier_spaceport","return_node_id":"frontier_collection"},{"type":"SetScheduleEnabled","schedule_id":"ore_haul_to_core","enabled":true},{"type":"SetScheduleEnabled","schedule_id":"parts_to_frontier_settlement","enabled":true}],"ticks":30}\n' \
  | PYTHONPATH=src python3 -m gaterail.main --stdio
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

Save, load, or swap scenarios through the bridge:

```bash
printf '{"ticks":3,"save_path":"saves/bridge_playtest.json"}\n{"load_path":"saves/bridge_playtest.json","ticks":0}\n' \
  | PYTHONPATH=src python3 -m gaterail.main --stdio
printf '{"scenario":"industrial_expansion","ticks":0}\n' | PYTHONPATH=src python3 -m gaterail.main --stdio
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

- `scenes/main.tscn` (Galaxy Map) — draws the fixture immediately, then requests a live `{"ticks":0}` snapshot from the Python stdio bridge and redraws when the backend responds. Exposes bridge status, save/load, scenario reset, schedules, finance, contracts, one-shot dispatch, pending-order cancellation, auto-run, map entity inspection, placeholder SVG assets, and an alert/status strip for command history, bridge errors, disruptions, and congestion.
- `scenes/local_region.tscn` (Local Region Construction) — drilled into from the galaxy map by selecting a world and pressing **View Local Region** in the inspector. Renders the topbar / left tool rail / center canvas / right HUD / bottom status bar from the Claude Design handoff archived at [`docs/design_handoff/local_region_construction/`](docs/design_handoff/local_region_construction/). Node, gate-hub, same-world rail, interworld gate-link, train purchase, and first route-schedule creation use backend-owned preview/validation before commit; route creation lets the player tune cargo, units per departure, and interval before preview. The right HUD Build Planner shows preview context, gate handoff route warnings, mining mission fuel/power/yield/haul-bucket context, and confirm/cancel actions. Built node layout metadata persists through snapshots/save-load. The `LAYERS` toggle renders backend-owned supply, demand, inventory, shortage, recipe-blocked, and transfer-pressure overlays. The **Galaxy Map** button returns to `main.tscn`.

Backend snapshots include `scenario_catalog` and `cargo_catalog`; Godot selectors consume those catalogs so new Python scenarios and cargo types do not need duplicate client-side registry edits.

Run the test suite:

```bash
pytest
```

The codebase now contains the full Sprint 9 objectives layer plus the Stage 2 bridge contract: cargo-delivery, frontier-support, and gate-recovery contracts; reputation; stable render snapshots; Python-level player commands; and a JSON-over-stdio mode for a future Godot subprocess. The fixed-tick backend is now the single source of truth ahead of the Stage 2 Godot 2D port.
