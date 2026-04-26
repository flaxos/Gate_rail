# Sprint Roadmap

## Purpose

This roadmap keeps development on rails while preserving room for iteration. Each sprint should end with something testable from the command line and a tighter understanding of what is actually fun.

## Current status

- Sprint 0 is complete: the game vision, design notes, and roadmap are documented.
- Sprint 1 is complete: the fixed-tick backend foundation, graph scenario, CLI runner, and tests are implemented.
- Sprint 2 is complete: freight trains can load, route, travel, unload, and relieve shortages in the CLI prototype.
- Sprint 3 is complete: worlds now track tier requirements, stability, support streaks, regression, promotion, and bottlenecks.
- Sprint 4 is complete: gates now reserve world power, unpowered gates block routes, and expansion pressure is visible.
- Sprint 5 is complete: Stage 1 operations now have recurring schedules, gate slots, finance, stockpiles, and monthly text tables.
- Sprint 6 is complete: worlds now have specialization profiles, recipe-driven exports, and a mining to manufacturing to research dependency chain.
- Sprint 7 is complete: route dispatch now reserves link capacity, queues overloaded departures, reports traffic pressure, and models recoverable disruptions.
- Sprint 8 is complete: the CLI now supports scenario discovery, scenario inspection, report filters, JSON save/load, schedule status tables, and a balanced benchmark scenario.
- Sprint 9 is complete: cargo-delivery, frontier-support, and gate-recovery contract kinds all resolve against tick state; reputation tracking, reward and penalty resolution, monthly contract reporting, stable render snapshots, player commands, and the JSON-over-stdio bridge are in place.
- Phase 2 is approved for this repository: Godot client work is allowed under `godot/`, while the Python backend remains authoritative and CLI/stdio-first.
- Sprint 10 is complete: the Godot bridge/client scaffold renders live snapshots, controls schedules/orders, displays finance/contracts, wires placeholder assets, and surfaces alerts.
- Sprint 11 is complete: the Godot client can auto-run the backend, inspect map entities, highlight selected objects, and show clearer link/train operational state.
- Sprint 12 hardening is complete: backend construction commands are immediate, validated, and test-covered for same-world rail/node expansion; delayed construction queues are deferred until build-time simulation is worth modeling.
- Sprint 13 is underway in the Local Region scene only. Slices 13A through 13D are complete: backend-owned previews drive node, rail, train, and route creation, with persisted local-world layout metadata, visible HUD preview context, ESC/tool-switch cancellation, an explicit cargo picker on route creation, and a Select-tool inspector for nodes and links. The galaxy map stays focused on run/inspect/dispatch/navigation.
- Sprint 14 is in progress. Slices 14A (buffer distribution) and 14B (transfer-limit pressure visibility) are complete: depots/warehouses auto-feed neighbouring demand within their per-tick transfer budget, and node snapshots expose `transfer_pressure` plus `saturation_streak` so the Local Region inspector can flag saturated bottlenecks.

## Long-term stages

Stage 1: Python simulation
- no graphics
- prove cargo demand, train schedules, gate slots, colony stockpiles, income, and costs
- output text tables per month

Stage 2: Godot 2D prototype
- tile-based rail map
- simple trains moving between stations
- cargo counters
- one wormhole gate
- route UI and gate schedule UI
- staged construction, starting with existing-galaxy expansion

Stage 3: Proper game expansion
- more worlds
- contracts
- corporate finance
- rival operators
- tech tree
- modular stations
- advanced rail types

## Working rules

- Keep the backend CLI-first until the simulation loop is worth presenting visually.
- Prefer fixed-tick deterministic simulation under the hood.
- Add tests whenever rules, formulas, validation, CLI contracts, or data model assumptions change.
- Avoid overbuilding train physics before the strategic and economic loop proves itself.
- Treat engine selection as a later delivery decision, not a current blocker.

## Sprint 0: Design Lock

Goal:
- establish the canonical game brief and the first implementation boundaries

Deliverables:
- accepted game vision document
- explicit design notes
- sprint roadmap
- initial terminology for worlds, tiers, gates, trains, stations, and cargo
- first MVP statement

Exit criteria:
- no major ambiguity about the backend-first direction
- clear agreement that the first prototype is CLI-first and system-focused

## Sprint 1: Simulation Foundation

Goal:
- create the backend structure for a multi-world logistics sim

Deliverables:
- package structure aligned to world, economy, transport, gate, sim, and cli concerns
- canonical game state model
- fixed-tick simulation loop
- basic world graph with rail links and gate links
- resource definitions for the MVP slice
- initial tests for state transitions and tick behavior

Exit criteria:
- a scenario can be loaded and stepped forward deterministically
- test coverage exists for core state updates

Completed state:
- `GameState` defines worlds, logistics nodes, rail links, gate links, current tick, and shortages
- `TickSimulation` advances deterministic fixed ticks
- `build_sprint1_scenario()` creates a two-world graph with three rail links and one gate link
- the CLI runs the Sprint 1 scenario with `gaterail --ticks N`
- tests cover graph shape, routing, deterministic ticks, shortages, and CLI output

## Sprint 2: First Freight Prototype

Goal:
- make cargo movement playable in the terminal

Deliverables:
- stations and depots
- trains with cargo capacity and route assignment
- producer and consumer nodes
- basic pathfinding across rail and gate links
- loading, unloading, and delivery resolution
- CLI commands to inspect and advance the simulation
- targeted tests for routing and delivery

Exit criteria:
- a player can assign freight flow and observe shortages or successful deliveries

Completed state:
- `FreightTrain` and `FreightOrder` are part of the fixed-tick `GameState`
- `build_sprint2_scenario()` adds three trains and three assigned freight orders
- trains load from origin storage, follow resolved rail/gate routes over multiple ticks, and unload at destinations
- terminal reports show dispatches, in-transit trains, deliveries, blockers, shortages, and route travel times
- tests cover scenario setup, dispatch, delivery, shortage relief, long-route cargo return, and CLI output

## Sprint 3: Frontier World Progression

Goal:
- make world development matter

Deliverables:
- world tiers and promotion requirements
- baseline needs for power, food, and industrial support
- storage and persistent shortages
- world specialization hooks
- CLI reporting for tier readiness and bottlenecks
- tests covering promotion and regression logic

Exit criteria:
- one world can move from fragile outpost to stable colony through sustained logistics

Completed state:
- `WorldState` tracks development progress, support streaks, shortage streaks, and last progression trend
- `progression.py` defines tier requirements and applies stability, regression, stall, and promotion rules each tick
- the Sprint 3 scenario can promote Brink Frontier from outpost to frontier colony through sustained delivered supplies
- terminal reports show whether worlds are improving, stalled, regressing, promoted, or max tier
- tests cover stockpile stalls, shortage regression, promotion, next-tier bottlenecks, and CLI progression output

## Sprint 4: Gate Pressure and Expansion

Goal:
- introduce wormholes as strategic infrastructure

Deliverables:
- gate hubs and activation rules
- power cost and throughput limits
- second world or second region connected through a gate
- cross-world dependency in at least one scenario
- tests for gate availability, power draw, and route selection

Exit criteria:
- the player can decide when a gate is worth activating to resolve a real bottleneck

Completed state:
- gate links resolve powered or underpowered status from world power margins each tick
- powered gates reserve world power and reduce remaining power margin
- route finding ignores underpowered gate links
- the Sprint 4 scenario adds Ashfall Spur behind a frontier-powered gate that starts underpowered
- terminal reports show powered gate counts, gate draw, power shortfalls, blocked freight, and expansion shortages
- tests cover gate power draw, route availability, blocked freight, powered dispatch, and CLI gate bottleneck output

## Sprint 5: Stage 1 Operations Ledger

Goal:
- make the backend measurable as a monthly terminal management sim

Deliverables:
- ticks treated as days for operations reporting
- recurring train schedules
- gate slot limits and slot exhaustion
- colony/world stockpile summaries
- fixed-tick income, costs, and cash balance
- month-end text tables for cargo moved, shortages, gate use, stockpiles, and finance

Exit criteria:
- `gaterail --ticks 30` produces a readable month-end operations ledger
- the player can see whether rail and gate operations are feeding colonies and making or losing money

Completed state:
- `FreightSchedule` supports recurring scheduled service
- dispatches reserve powered gate slots before loading cargo
- `FinanceState` records delivery revenue, dispatch costs, gate power costs, and cash balance
- `operations.py` aggregates month-end cargo, shortage, gate, stockpile, and finance summaries
- the named Sprint 5 scenario prints a monthly operations table after 30 ticks
- tests cover recurring schedules, gate slot exhaustion, delivery revenue, monthly ledgers, and CLI table output

## Sprint 6: Economic Identity

Goal:
- make worlds feel different and useful to one another

Deliverables:
- specialized world archetypes such as mining, farming, refining, manufacturing, recycling, research
- differentiated demand and export profiles
- stronger financial and production tradeoffs
- comparative scenario reports
- tests for specialization-driven output and demand behavior

Exit criteria:
- a network of worlds shows real interdependence instead of isolated loops

Completed state:
- `SpecializationProfile` defines import/export identities for manufacturing, mining, and survey worlds
- `ProductionRecipe` turns delivered inputs into specialized exports during the fixed-tick economy phase
- the Sprint 6 scenario links Brink Frontier ore, Vesta Core manufacturing, and Ashfall Spur research equipment
- recurring schedules move parts and research equipment so the monthly ledger shows cross-world dependence
- terminal reports show active economic identities and month-end specialized output totals
- tests cover specialization profiles, mining output, manufacturing from delivered ore, survey research output, monthly ledgers, and named Sprint 6 CLI output

## Sprint 7: Traffic, Capacity, and Failure

Goal:
- stress the network so planning quality matters

Deliverables:
- congestion and throughput caps
- maintenance or disruption hooks
- queueing pressure at stations and gate hubs
- better alerts and telemetry
- tests for degraded and recovered states

Exit criteria:
- the game produces meaningful logistics failures that can be diagnosed and fixed

Completed state:
- dispatch now reserves one per-tick capacity slot on every rail and gate link in a train route
- queued freight events explain when a train cannot depart because a link is full or disrupted
- `NetworkDisruption` models timed link capacity reductions and automatic recovery
- the Sprint 7 scenario adds a one-slot core yard throat and a two-tick outer gate maintenance outage
- tick reports show traffic alerts, and month-end ledgers summarize peak pressure, full ticks, and disrupted ticks
- tests cover the chokepoint queue, disruption block, recovery dispatch, monthly traffic pressure, and default Sprint 7 CLI output

## Sprint 8: Playability Pass

Goal:
- make the CLI prototype coherent enough for regular iteration

Deliverables:
- scenario setup commands
- richer reports
- save and load support
- benchmark scenarios
- balancing pass on the first progression arc

Exit criteria:
- the project supports repeatable playtests and design iteration without ad hoc code edits

Completed state:
- `sprint8` is the default balanced benchmark scenario and keeps the Sprint 7 lessons with less severe first-month blockage
- `gaterail --list-scenarios` lists built-in scenarios, aliases, and the default playtest target
- `gaterail --inspect` prints setup details without advancing simulation time
- `--report` filters tick and month-end output to focused sections such as traffic, finance, schedules, and stockpiles
- JSON save/load supports repeatable playtests and resumes with report history intact for month-end ledgers
- month-end ledgers now include schedule status tables alongside finance, cargo, gate, traffic, and stockpile tables

## Sprint 9: Contracts and Objectives

Goal:
- turn the simulation from observation into explicit player goals

Deliverables:
- contracts for cargo delivery, frontier support, and gate recovery
- objective scoring for monthly playtests
- penalties and bonuses tied to missed or fulfilled commitments
- scenario presets that ask the player to optimize different outcomes
- CLI reports that explain what the player is trying to achieve next

Exit criteria:
- a playtest has concrete success/failure pressure beyond "watch the system run"

Slice 1 completed state:
- `Contract` and `ContractStatus` model a cargo-delivery objective with due tick, target units, reward cash, penalty cash, reward reputation, and penalty reputation
- `GameState.reputation` tracks player-corp standing as a single integer (future-ready for per-faction reputation with rival operators)
- `contracts.py` resolves deliveries into contract progress, fulfilling on target and failing once when the deadline passes
- the Sprint 8 benchmark seeds three contracts (food relief, ore quota, medical lifeline); the balanced run fulfills one and fails two to create concrete pressure
- tick reports show active contract progress and resolution events; monthly ledgers summarize fulfilled, failed, and active totals plus ending reputation
- scenario inspection prints an `Active Contracts` table; the CLI gains a `contracts` report section filter
- save/load round-trips contract state and reputation deterministically

Post-slice-1 cleanup: legacy daily-colony simulation (`Simulation`, `colony.py`, `world.py`, `train.py`, `schedule.py`, `finance.py`, `WormholeGate`) removed to give Sprint 9 slices 2–4 a single backend path.

Slices 2–4 completed state:
- `ContractKind.FRONTIER_SUPPORT` tracks supported-or-promoted ticks on a target world via the progression report; the contract's `progress` counter persists across tier promotions so a bump at the moment of promotion still counts
- `ContractKind.GATE_RECOVERY` tracks consecutive operational ticks on a target gate link (powered and effective capacity > 0); a disruption or power shortfall resets the streak
- contract resolution now runs after world progression, so FRONTIER_SUPPORT reads the freshly updated trend; cargo-delivery behavior is unchanged
- `add_contract` validates kind-specific required fields (destination/cargo for CARGO_DELIVERY, target world for FRONTIER_SUPPORT, target gate link for GATE_RECOVERY)
- three scenario presets ship: `sprint9_logistics` stretches sprint8 with a 10-unit PARTS contract into Ashfall; `sprint9_frontier` adds a support-streak contract on Brink Frontier; `sprint9_recovery` turns the frontier-outer gate into a full outage for ticks 1–12 and adds a 3-tick recovery contract
- persistence round-trips the new `target_world_id`, `target_link_id`, and `progress` fields; scenario inspection and tick/monthly reports render all three kinds

Stage 2 bridge completed state:
- `render_snapshot()` returns a stable JSON object with `SNAPSHOT_VERSION = 1`, covering tick, worlds, nodes, links, trains, schedules, orders, contracts, finance, and reputation separately from the rich text reports
- `PlayerCommand` supports `SetScheduleEnabled`, `DispatchOrder`, and `CancelOrder` through `GameState.apply_command(cmd)`
- `gaterail --stdio` reads newline-delimited JSON, applies commands, steps N ticks, and emits one render snapshot JSON line per input line
- the bridge architecture is Python subprocess plus JSON over stdio; Python owns deterministic galaxy-scale world coordinates, and Godot will own visual/intra-world placement metadata

Deferred (not blocking Stage 2 prep):
- optional accept/offer flow so contracts can be refused or negotiated before becoming active
- per-faction reputation (the single integer stays until rival operators arrive)
- full construction commands for building stations, rails, gates, trains, schedules, and eventually new worlds

## Sprint 10: Godot Bridge Prototype

Goal:
- prove Stage 2 can render and control the Python simulation without rewriting the backend

Deliverables:
- `godot/` sibling project scaffold
- `GateRailBridge` autoload that launches `gaterail --stdio`
- one main 2D scene that renders `render_snapshot()` worlds, links, nodes, trains, contracts, finance, and reputation
- route/schedule controls that send the existing Stage 2 player commands
- smoke tests or scripts that verify the bridge contract outside the editor

Exit criteria:
- Godot can start the Python subprocess, receive snapshots, toggle a schedule, queue a one-shot order, step the sim, and redraw from the returned snapshot

Working slice:
- scaffold a Godot 4 project under `godot/`
- add a `GateRailBridge` autoload that can send JSON lines and parse snapshot JSON
- add one `Main` scene that draws worlds, links, nodes, trains, and key HUD labels from a fixture or live bridge snapshot
- keep all simulation decisions in Python

Slice 1 completed state:
- `godot/project.godot` defines the Stage 2 client and autoloads `GateRailBridge`
- `Main` renders a fixture snapshot immediately, then requests a live `{"ticks":0}` snapshot from `gaterail --stdio`
- `GateRailBridge` computes the repository root from `res://`, starts the Python subprocess with an absolute command, validates `snapshot_version`, guards writes, reports bridge errors, and shuts down the subprocess on exit
- the scene exposes step and schedule-toggle controls backed by the live stdio bridge
- Godot headless smoke and Python tests pass

Slice 2 completed state:
- `Main` now has a visible bridge status panel showing bridge running/stopped state, snapshot source, and schedule count
- the hardcoded food-service toggle was replaced with a schedule list generated from the live snapshot
- each schedule row shows active state, cargo, units, route, next departure tick, and an enable/disable command wired to `SetScheduleEnabled`
- command results from the bridge are surfaced in the status text so live backend control is visible in-scene

Slice 3 completed state:
- `Main` now includes a finance and reputation panel sourced from the current snapshot
- contracts render in a UI panel with progress, due tick, and fulfilled/failed color state
- the dispatch form is populated from snapshot trains, nodes, and cargo ids
- `Queue DispatchOrder` sends a one-shot order with `ticks:0`, so it appears as pending before simulation advances
- pending active orders render in a list with per-order `CancelOrder` buttons

Slice 4 completed state:
- Antigravity placeholder SVGs are documented and wired into the Godot scene
- worlds, nodes, trains, schedule cargo icons, contract rows, and primary action buttons now use the placeholder asset pack with shape/color fallbacks
- `PHASE2_UI_WIREFRAME.md` captures the Claude Design handoff summary so implementation is not dependent on a temporary HTML export

Slice 5 completed state:
- `Main` now includes the wireframe alert/status strip as a bottom panel
- the strip keeps recent bridge command results and bridge errors visible as compact chips
- current link disruptions, degraded capacity, and high gate slot usage are rendered as live warning/congestion chips from the snapshot

## Sprint 11: Playable Operations UI

Goal:
- make the current Sprint 8/Sprint 9 scenarios playable from Godot without construction, so the bridge/client loop is solid before track laying begins

Deliverables:
- pause, step, and run controls backed by stdio bridge messages
- click selection for worlds, nodes, links, and trains
- inspector panel showing selected entity state
- clearer rail/gate links, capacity labels, disrupted/degraded links, and in-transit train positions

Exit criteria:
- a player can run, inspect, and change scenario outcomes from the Godot UI without terminal commands

Completed state:
- `Main` has Play/Pause auto-run controls that advance the live backend through `ticks:1` bridge messages
- map clicks select worlds, nodes, links, and trains without adding backend rules to Godot
- the inspector reports operational state for the selected entity, including cargo, storage, power, route, capacity, and disruption details
- in-transit trains are drawn along their active route, selected entities are highlighted, and links show rail/gate mode plus effective/base capacity labels
- the client layout is responsive: side panels anchor to the viewport edges, the alert strip spans the bottom, and the network map is computed into the available center area at windowed and fullscreen sizes

## Sprint 12: Track Construction Rules and Backend Commands

Goal:
- define the core track-laying game rules before building the Godot construction UI

Deliverables:
- construction rules for buildable node roles: extractor, industry, depot, warehouse, settlement connector, and gate hub
- backend command for building logistics nodes on existing worlds
- backend command for building rail links between valid nodes
- validation for duplicate links, world boundaries, invalid endpoints, cash costs, and storage/transfer defaults
- JSON bridge error frames for invalid construction
- snapshot support for newly built entities and construction-relevant metadata

Exit criteria:
- backend tests prove that constructed nodes and rail links can alter routing and logistics outcomes

Completed state:
- Models now support per-link build cost/time metadata and the `warehouse` node role.
- `link_build_cost`, `node_build_cost`, `node_upgrade_cost`, and `train_purchase_cost` rules are centralized.
- Backend handles `BuildNode`, `BuildLink`, `DemolishLink`, `PurchaseTrain`, and `UpgradeNode` commands with cash checks and validation.
- `BuildLink` is intentionally rail-only for Sprint 12 and rejects self-links, cross-world rail, duplicate endpoint pairs, invalid endpoints, and invalid capacity/travel values.
- Snapshot and persistence round-trip newly built entities plus construction-relevant link metadata.
- Construction queues are deferred; Sprint 12 construction completes immediately.
- Tests cover validation errors, cash deduction, warehouse defaults, duplicate checks, persistence, and route changes from a constructed rail link.

## Sprint 13: Godot Track Construction Mode

Goal:
- turn backend construction rules into the first hands-on track-laying UI

Deliverables:
- build-mode toggle in Godot
- click-to-place logistics nodes on existing worlds
- click-to-connect rail links between valid nodes
- cost preview, valid/invalid placement feedback, and bridge error chips
- immediate redraw from returned snapshots

Exit criteria:
- the player can add rail infrastructure to the benchmark scenario from Godot and see it affect routing

Slice 13A completed state:
- `PreviewBuildNode` and `PreviewBuildLink` validate placement, cost, build-time metadata, defaults, affordability, and normalized build commands without mutating state.
- `BuildNode` can persist local layout coordinates, and snapshots/save-load round-trip that metadata.
- `BuildLink` can derive rail travel time from persisted local node layout when the client omits `travel_ticks`.
- The Local Region scene requests backend previews before committing node, gate-hub, or rail construction, then sends the normalized backend-owned build command on the second click.
- Godot no longer duplicates node or rail construction costs; invalid previews return as command results instead of bridge errors.
- Tests cover preview parsing, non-mutating previews, invalid preview results, persisted layout metadata, bridge preview behavior, and layout-derived rail travel ticks.

Slice 13B completed state:
- `docs/construction_rules.md` is the canonical local construction rules reference for node roles, rail constraints, layout travel-time derivation, train purchase, route schedules, and deferred queue/gate work.
- `PreviewPurchaseTrain` and `PreviewCreateSchedule` extend the backend-owned preview contract to train and route creation.
- `CreateSchedule` creates recurring freight schedules from existing infrastructure after validating train location, idle state, cargo units, interval, route existence, and next departure.
- The Local Region Train tool now supports a first route loop: click an empty node to preview/buy a train, or click a node with an idle train to select an origin and click a destination to preview/create a route schedule.
- Godot no longer hardcodes train purchase cost; route validity and route travel metadata come from the backend preview.
- Tests cover train purchase previews, schedule creation, schedule previews, bridge-contained invalid preview results, and snapshot visibility of created schedules.

Slice 13C completed state:
- The right HUD's placeholder construction queue is now a `Build Planner` panel.
- The planner shows active tool guidance, selected route train/origin context, backend preview status, target id, costs, build time, travel time, capacity, storage/transfer, route details, cargo, units, and interval where available.
- Valid previews expose HUD `Confirm` and `Cancel` actions, so the player no longer has to rely only on the bottom status strip or a second map click.
- The planner remains immediate-mode; delayed construction queues are still deferred until build-time simulation is implemented.

Slice 13D completed state:
- ESC and tool-switch now uniformly cancel any in-flight preview, route-builder selection, rail-origin pick, cargo popup, and inspection. The status strip explains the cancellation.
- Route creation no longer auto-commits to a suggested cargo; clicking a destination opens a cargo popup populated from the origin inventory/production and the destination demand, with the auto-suggestion marked. Backend `PreviewCreateSchedule` and `CreateSchedule` already accept any cargo, so no contract change was needed.
- The Select tool now populates the Build Planner with an inspector for the clicked node or link (kind, world, storage, transfer, inventory/demand/production, shortages, trains here, touching links, mode, travel ticks, capacity, in-transit trains, disruption reasons, powered state, build cost).
- Tests cover cargo override round-tripping through preview and create, parametrized cargo persistence on the schedule, and the cancellation contract that invalid previews leave state clean and a follow-up valid preview still works.

## Sprint 14: Industry, Depot, and Warehouse Logistics

Goal:
- make local-world rail construction matter as the main game loop

Deliverables:
- warehouse/depot buffering rules and visible storage pressure
- clearer extractor to industry to depot flows
- node transfer constraints that make local track layout meaningful
- UI overlays for supply, demand, inventory, and shortages

Exit criteria:
- the player can improve a local world's supply chain by connecting production, storage, demand, and depot nodes

Slice 14A completed state:
- New tick phase `buffer_distribution` runs after node production and before node demand. Depots and warehouses push buffered inventory across same-world rail links to neighbouring nodes whose declared demand is still unmet, bounded by the buffer node's `transfer_limit_per_tick` across all outflows. Cargo never auto-jumps gate links.
- Per-tick reports include a `buffer_distribution` rollup keyed by source then target then cargo.
- Node snapshots expose `buffer_fill_pct` (only on depot/warehouse, null elsewhere) and `served_last_tick` (only on depot/warehouse, empty elsewhere), so the Godot inspector can show buffering state.
- Tests cover deficit-only filling, transfer-limit budgeting across neighbours, warehouse-kind parity, non-buffer kinds opting out, gate-link isolation, multi-tick supply without trains, and the snapshot contract.

Slice 14B completed state:
- `GameState` tracks `transfer_used_this_tick` and `transfer_saturation_streak` per node. Reset at the start of each tick; bumped by the buffer phase (both source and target by accepted units), train loads at the origin, and train unloads at the destination.
- After freight movement, `update_transfer_saturation_streaks` increments a node's streak when used/limit ≥ 0.95, and resets it otherwise.
- Node snapshots expose `transfer_used`, `transfer_pressure` (used/limit, 3dp), and `saturation_streak` for every node, alongside the existing `transfer_limit`.
- The Godot Local Region inspector now renders transfer as `used / limit (pct%)` with a steel/green/amber/red color depending on pressure, and shows a "SATURATED" or "Approaching limit" note when the saturation streak fires.
- Tests cover buffer-side bumping on both ends, train load/unload bumping, multi-tick streak growth, streak reset when idle, the inclusive 95% threshold, and the snapshot contract.

## Sprint 15: Gate Expansion, Trains, and Schedule Creation

Goal:
- connect local track networks to interworld wormhole logistics

Deliverables:
- backend commands for gate hubs and gate links
- train purchase/build command
- schedule creation command
- Godot UI for gate construction, train purchase, and schedule creation
- clear cost, power, capacity, and route feedback

Exit criteria:
- the player can expand an existing network with rail, warehouses/depots, gates, trains, and schedules from Godot

## Interactive cadence

For collaborative development:

1. Pick one sprint target.
2. Break it into the next smallest testable vertical slice.
3. Implement that slice.
4. Run tests and inspect terminal output.
5. Decide whether the result is fun, clear, and extensible before expanding scope.

## Current next step

Slice 14B landed (transfer-limit pressure visibility). Sprint 14 continues with 14C (extractor → industry recipe round-trip) and 14D (local overlays for supply / demand / shortage / inventory).
