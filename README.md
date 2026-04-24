# GateRail

GateRail is a CLI-first simulation project for a logistics and world-building game about **trains, wormholes, frontier development, and interplanetary supply chains**.

The long-term game fantasy combines three angles:
- railroad tycoon across impossible distances,
- industrial supply-chain optimizer,
- frontier builder growing worlds from outposts into major civil and industrial hubs.

The current repository focus is the backend. We are building the simulation in Python first so the rules, data model, and progression can be tested in terminal workflows before committing to a final engine or presentation layer.

## Product direction

GateRail is built around these assumptions:
- trains are the dominant logistics layer for bulk cargo and mass transit,
- wormholes are powerful but energy-hungry infrastructure,
- worlds progress through development tiers,
- expansion depends on building stable interdependent supply chains,
- the product surface stays CLI-first during backend development.

This is not a visual prototype yet. It is a systems-first game project.

## Design goals

- Keep the simulation deterministic and testable.
- Make the game playable from terminal commands as early as possible.
- Use data and rules that can survive either a future custom engine path or a frontend client layered on top.
- Favor a small, proven core loop over broad but shallow feature lists.

## Long-term staging

Stage 1 is the current Python simulation: no graphics, with cargo demand, train schedules, gate slots, colony stockpiles, income, costs, and monthly text tables.

Stage 2 is a future Godot 2D prototype: tile-based rail, simple moving trains, cargo counters, one wormhole gate, route UI, and gate schedule UI.

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
- [SPRINTS.md](SPRINTS.md): sprint-by-sprint development plan

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

Run the test suite:

```bash
pytest
```

The codebase now contains the full Sprint 9 objectives layer — cargo-delivery, frontier-support, and gate-recovery contract kinds plus reputation — layered on the Sprint 8 CLI playability prototype, with three new scenario presets (`sprint9_logistics`, `sprint9_frontier`, `sprint9_recovery`) exercising each kind. The legacy daily-colony prototype has been retired so the fixed-tick backend is now the single source of truth ahead of the Stage 2 Godot 2D port.
