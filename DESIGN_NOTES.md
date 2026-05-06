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
- Gate Horizons is the origin-era Horizon Artefact story; GateRail is the later Railgate Age consequence.
- Railgates are derivative aperture systems: paired, route-bound, energy-hungry, throughput-limited, and valuable because trains provide exact alignment and standardized freight.
- Transit Combines and megacorporations should read as the major contract powers, not fantasy factions.
- Real-time play should be implemented on top of a fixed-tick backend model.
- The first prototype should favor operational train logistics over detailed signal-level realism.
- Engine selection is intentionally deferred until the backend proves the game loop.
- Sprint 1 keeps the older daily colony prototype intact while adding the new fixed-tick graph foundation.
- Sprint 2 adds operational freight trains on the fixed-tick graph while keeping dispatch simple and order-driven.
- Sprint 3 makes world development reactive to logistics support through stability, bottlenecks, and tier promotion.
- Sprint 4 makes Railgate links power-limited infrastructure that can block or enable expansion corridors.
- Sprint 5 aligns the Python backend with Stage 1 by adding recurring schedules, Railgate slots, finance, stockpiles, and monthly text tables.
- Sprint 6 gives worlds economic identities through specialization profiles and recipe-driven exports, creating a visible mining to manufacturing to research dependency chain.
- Sprint 7 makes network stress diagnosable through per-link capacity reservations, queue telemetry, timed disruptions, and recovery reports.
- Sprint 8 makes the CLI usable for repeatable playtests through scenario discovery, inspection reports, focused report filters, JSON save/load, and a balanced benchmark scenario.
- Sprint 9 slice 1 turns the sim into a goal-driven playtest via cargo-delivery contracts with due ticks, cash rewards, cash penalties, and a single integer reputation score; reputation is intentionally a single number now so it can split into per-faction standings once rival operators and other corps land in later slices.
- Sprint 9 slices 2-4 extend the objectives layer with frontier-support contracts (progress accumulates on ticks where the target world's trend is improving or promoted), Railgate-recovery contracts (consecutive operational-tick streak on a target Railgate link, with the streak resetting when the link loses power or capacity), and three scenario presets so each contract kind has a dedicated playtest harness; contract resolution now runs after world progression so the frontier-support check reads a freshly updated trend.
- Post-Sprint-9 cleanup: the legacy daily-colony simulation path (`Simulation`, `colony.py`, `world.py`, `train.py`, `schedule.py`, `finance.py`) has been removed so the fixed-tick backend is the single source of truth heading into the Stage 2 Godot 2D port.
- Stage 2 integration will use a Python subprocess with newline-delimited JSON over stdio. The Python backend owns deterministic galaxy-scale world coordinates in `render_snapshot()` and persists local node layout metadata; Godot proposes intra-world placement and owns camera/presentation metadata.
- Full construction remains the Stage 2 player-agency target, but it should be sliced after the bridge lands: first expand an existing galaxy through schedules/orders and existing infrastructure controls, then add build commands for stations, rails, Railgate anchors, trains, and finally new worlds.
- Local Region Construction view follows the Claude Design handoff archived at `docs/design_handoff/local_region_construction/`. Galaxy Map (`scenes/main.tscn`) and Local Region (`scenes/local_region.tscn`) are separate Godot scenes sharing the `GateRailBridge` autoload, with a `SceneNav` autoload carrying the selected `world_id` across the scene change.
- Local construction rules are now pinned in `docs/construction_rules.md`; clients should preview node, rail, train, and route-schedule actions through Python before committing.
- The Local Region right HUD now treats construction as a preview-driven build planner rather than a timed queue; delayed build jobs remain deferred.
- Local Region layer overlays are presentation-only and consume backend snapshot fields for supply, demand, storage fill, shortages, recipe-blocked inputs, and transfer pressure. Godot should not infer logistics rules beyond choosing glyphs, colors, and counts.
- Interworld Railgate-link construction is now backend-owned through `BuildLink(mode="gate")`; clients can propose existing Railgate endpoints, but Python owns endpoint validation, default capacity/power, cost, power-shortfall context, and whether a newly built corridor is usable.
- Route and schedule previews now expose backend-owned Railgate handoff context. Clients should render the returned gate ids, endpoint worlds, power/slot/disruption state, and warnings rather than rechecking corridor rules locally.
- Local Region route creation lets the player choose cargo, units per departure, and interval before preview; Python remains authoritative for validating those values and returning normalized schedule commands.
- The next major presentation layer should not be scoped as "3D first." It should be scoped as a backend-owned facility layer first: stations, depots, warehouses, industries, extractors, and Railgate anchors gain internal components, ports, loaders, unloaders, buffers, platforms, and factory blocks. A later 3D view should render that facility state rather than invent simulation rules in Godot.
- Before any 3D facility presentation, the core industrial fantasy needs deeper backend rules: elemental resources, ore grades, smelting/refining, manufacturing tiers, semiconductors, advanced components, power-plant inputs, Railgate-energy inputs, space extraction, and outpost construction.
- The resource catalog should be data-driven and able to grow toward periodic-table scale, but implementation should start with a playable subset and add elements only when they create distinct logistics decisions.
- Local rail should not remain endpoint-only. Future backend work should add track alignment geometry, underground vacuum-tube constraints, branches, junctions, stop/path signals, train consists, and cargo wagon compatibility. Godot should render and edit these plans through backend previews, not own routing or signaling rules.

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
- resources and the resource catalog,
- raw deposits, ore grades, and refining yields,
- production and consumption,
- smelting, refining, alloying, chemistry, semiconductor, and assembly recipes,
- storage,
- shortages and surpluses,
- promotion requirements.

### Transport layer

Responsible for:
- tracks and links,
- track alignment geometry and waypoints,
- surface rail versus underground vacuum-tube constraints,
- branches, junctions, station throats, and portals,
- stop signals, path signals, blocks, and route reservations,
- stations and depots,
- trains, consists, cargo wagons, and typed capacity,
- routes,
- congestion and throughput constraints,
- fixed-tick mining missions as logistics actors when space extraction lands.

### Facility layer

Responsible for:
- station, depot, warehouse, industry, extractor, and gate-hub internals,
- platforms,
- cargo loaders and unloaders,
- storage bays and buffers,
- crushers, sorters, smelters, refineries, chemical processors, fabricators, electronics assemblers, semiconductor lines, and factory blocks,
- typed input/output ports,
- internal component connections,
- facility-level throughput and blocked-flow diagnostics.

### Railgate layer

Responsible for:
- Railgate anchors and receiving terminals,
- paired aperture links,
- activation and alignment logic,
- throughput,
- power draw and operating burden,
- stored charge, aperture-efficiency upgrades, and rare/exotic inputs once the power economy is expanded.

### Space extraction layer

Responsible for:
- remote sites such as belts, moons, debris fields, gas pockets, and anomalies,
- mining ships as fixed-tick logistics actors,
- orbital yards and collection stations,
- outpost construction requirements,
- cargo returns into the rail and gate network.

## Modeling guidance

### Time

Use discrete fixed ticks internally. Frontend or CLI controls can expose pause, resume, faster stepping, or batched advancement later.

### Trains

For the MVP:
- trains need identity, capacity, route, speed, and cargo compatibility,
- stations need queue and transfer behavior,
- links need travel time and simple capacity constraints.

As industry deepens, train capacity should evolve into typed consists and cargo wagons. Bulk ore, liquids, electronics, construction modules, reactor materials, and exotics should eventually need different wagon compatibility. This should start as typed capacity maps before any detailed wagon physics.

Detailed braking physics should wait. Simple stop signals, path signals, and block reservations should arrive earlier because dense industry yards need understandable waiting and conflict reports.

### Track Planning

Rail construction should evolve from A-to-B links into backend-owned track alignments. A track plan can start as endpoint nodes plus waypoint/control-point geometry. The backend should persist that geometry, price it, derive travel time from it, and expose it in snapshots. Godot should draw curved rails from the snapshot and send preview requests when the player edits control points.

Underground vacuum tubes are allowed to be more direct than surface rail, but they should still have portals, curve limits, power or maintenance burdens, and signal/slot constraints.

### Facilities

Facilities should become the bridge between abstract local nodes and the eventual 3D station/depot/hub view. The backend should own facility components and ports before any 3D scene is built. Godot can render the facility layer in 2D first, then render the same snapshot in 3D later.

Factory blocks should evolve into typed processing components. A smelter, refinery, electronics assembler, semiconductor line, and aperture-control assembly bay should have distinct inputs, outputs, power draw, rates, and blocked-flow reasons.

### Resources

Treat resources as a data catalog with stable ids, display names, categories, and optional metadata such as element symbol, isotope, grade, rarity, discovery state, and unlock requirements. Do not hardcode UI behavior around one small enum once the industry layer expands.

The first playable chain should prove one end-to-end path:
- raw ore or regolith,
- sorting or concentration,
- smelting/refining into an element or bulk material,
- manufacturing into parts/electronics/semiconductors,
- advanced assembly into power systems or aperture control components.

### Space extraction

Space extraction should extend the logistics game, not become a piloting game. Mining ships can be modeled as dispatchable fixed-tick missions with cargo yield, travel time, fuel/power needs, and return nodes. Trains remain essential because they build and supply the orbital yards, outposts, and collection stations that make those missions useful.

### Power economy

Power should move from a mostly static world stat toward an industrial system. Power plants should consume fuel, reactor materials, coolant, parts, or exotic inputs. Gate hubs should reserve power and eventually consume charge for high-throughput operation. This creates a direct reason to mine rare elements and manufacture advanced components.

### Worlds

Worlds should be modeled as economic and logistical entities, not just terrain containers. A world's tier should express what it can sustain, what it demands, and what role it can play in the wider network.

### Railgates

Railgates should feel powerful but expensive. They are not free teleport edges or mastered precursor gates. Their purpose is to let the player reshape the logistics graph at major strategic cost.

## MVP boundary

The first real proof point is narrow:

The player can bootstrap a frontier colony into a self-sustaining industrial hub using rail logistics and one power-hungry Railgate corridor to solve a major bottleneck.

Anything outside that should be treated as a later expansion unless it is required to make this scenario work.

## Deferred systems

The following are valid future systems but should not block the first playable prototype:
- passenger simulation beyond abstract demand,
- fine-grained signaling and dispatching,
- disruption and maintenance systems,
- contracts and market pricing,
- advanced policy systems,
- richer scenario authoring and comparative analytics,
- graphical polish beyond the thin Godot client,
- 3D facility presentation before resource, power, and space-extraction rules are proven.
