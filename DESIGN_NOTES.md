# Design Notes

## Scope boundary

GateRail is currently a backend-first, CLI-first game project. The purpose of the current phase is to discover and validate the simulation through terminal workflows before choosing a permanent presentation layer or engine path.

This means:
- simulation rules come before visuals,
- command-line playability comes before graphical UX,
- deterministic state transitions matter more than animation,
- architecture should stay portable enough for later engine decisions.

## Core design pillars

1. **Deterministic execution**  
   Given the same state and inputs, the simulation should step forward identically.

2. **Readable terminal output**  
   Important state must be understandable in plain text reports and inspection commands.

3. **Layered simulation**  
   Strategic, economic, transport, and gate systems should remain separable.

4. **Constrained realism**  
   Use enough physical and economic detail to create good decisions, not to simulate everything.

5. **Progression through logistics**  
   Worlds should develop because the network supports them, not because the player merely clicks an upgrade.

6. **Testable rules**  
   Changes to formulas, validation, state transitions, and CLI contracts should be covered by focused tests.

## Accepted design decisions

- The game fantasy combines railroad tycoon, industrial optimization, and frontier world-building.
- Trains are the main logistics layer, especially for high-capacity freight.
- Wormholes are strategic infrastructure with meaningful power cost.
- Real-time play should be implemented on top of a fixed-tick backend model.
- The first prototype should favor operational train logistics over detailed signal-level realism.
- Engine selection is intentionally deferred until the backend proves the game loop.
- Sprint 1 keeps the older daily colony prototype intact while adding the new fixed-tick graph foundation.
- Sprint 2 adds operational freight trains on the fixed-tick graph while keeping dispatch simple and order-driven.
- Sprint 3 makes world development reactive to logistics support through stability, bottlenecks, and tier promotion.
- Sprint 4 makes gate links power-limited infrastructure that can block or enable expansion routes.
- Sprint 5 aligns the Python backend with Stage 1 by adding recurring schedules, gate slots, finance, stockpiles, and monthly text tables.
- Sprint 6 gives worlds economic identities through specialization profiles and recipe-driven exports, creating a visible mining to manufacturing to research dependency chain.
- Sprint 7 makes network stress diagnosable through per-link capacity reservations, queue telemetry, timed disruptions, and recovery reports.
- Sprint 8 makes the CLI usable for repeatable playtests through scenario discovery, inspection reports, focused report filters, JSON save/load, and a balanced benchmark scenario.
- Sprint 9 slice 1 turns the sim into a goal-driven playtest via cargo-delivery contracts with due ticks, cash rewards, cash penalties, and a single integer reputation score; reputation is intentionally a single number now so it can split into per-faction standings once rival operators and other corps land in later slices.
- Sprint 9 slices 2-4 extend the objectives layer with frontier-support contracts (progress accumulates on ticks where the target world's trend is improving or promoted), gate-recovery contracts (consecutive operational-tick streak on a target gate link, with the streak resetting when the link loses power or capacity), and three scenario presets so each contract kind has a dedicated playtest harness; contract resolution now runs after world progression so the frontier-support check reads a freshly updated trend.
- Post-Sprint-9 cleanup: the legacy daily-colony simulation path (`Simulation`, `colony.py`, `world.py`, `train.py`, `schedule.py`, `finance.py`) has been removed so the fixed-tick backend is the single source of truth heading into the Stage 2 Godot 2D port.

## Simulation layers

### Strategic layer

Responsible for:
- worlds,
- development tiers,
- specialization,
- population and stability,
- unlock and expansion pressure.

### Economic layer

Responsible for:
- resources,
- production and consumption,
- storage,
- shortages and surpluses,
- promotion requirements.

### Transport layer

Responsible for:
- tracks and links,
- stations and depots,
- trains and capacity,
- routes,
- congestion and throughput constraints.

### Gate layer

Responsible for:
- wormhole hubs,
- gate links,
- activation logic,
- throughput,
- power draw and operating burden.

## Modeling guidance

### Time

Use discrete fixed ticks internally. Frontend or CLI controls can expose pause, resume, faster stepping, or batched advancement later.

### Trains

For the MVP:
- trains need identity, capacity, route, speed, and cargo compatibility,
- stations need queue and transfer behavior,
- links need travel time and simple capacity constraints.

Detailed block signaling, train assembly, or fine-grained rail physics should wait until the game proves they materially improve play.

### Worlds

Worlds should be modeled as economic and logistical entities, not just terrain containers. A world's tier should express what it can sustain, what it demands, and what role it can play in the wider network.

### Gates

Gates should feel powerful but expensive. They are not free teleport edges. Their purpose is to let the player reshape the logistics graph at major strategic cost.

## MVP boundary

The first real proof point is narrow:

The player can bootstrap a frontier world into a self-sustaining industrial colony using rail logistics and one power-hungry wormhole hub to solve a major bottleneck.

Anything outside that should be treated as a later expansion unless it is required to make this scenario work.

## Deferred systems

The following are valid future systems but should not block the first playable prototype:
- passenger simulation beyond abstract demand,
- fine-grained signaling and dispatching,
- disruption and maintenance systems,
- contracts and market pricing,
- advanced policy systems,
- orbital and space-lane logistics,
- richer scenario authoring and comparative analytics,
- graphical client work.
