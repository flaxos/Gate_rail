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
- Sprint 13 is complete in the Local Region scene: backend-owned previews drive node, rail, train, and route creation, with persisted local-world layout metadata, HUD preview context, cancellation, cargo picking, and Select-tool inspection.
- Sprint 14 is complete: depots/warehouses move cargo through buffer rules, node snapshots expose transfer bottlenecks, per-node recipes drive local industry, and Local Region overlays make supply/demand/storage/shortage pressure visible.
- Facility, industry, and rail-depth planning is accepted: station/depot/hub 3D should wait until backend-owned facilities, elemental resource chains, power inputs, space extraction, outpost logistics, and richer rail networks exist.
- Sprints 16-27 are complete through the current working tree: facility components/internal wiring, resource chains, typed industry, gate power support, power generation, remote extraction/outpost operations, directional gates, train consists, multi-stop schedules, cargo-flow snapshots, schedule edit/delete management, bridge save/load, and early/expanded playtest scenario presets are all covered by backend tests and Godot bridge/UI wiring.
- Sprint 28A/28B are implemented, with a backend payoff extension now covered by tests: `mining_to_manufacturing` / `mining_loop` can dispatch a mining mission, haul ORE, smelt it into METAL, fabricate PARTS/construction materials, deliver PARTS to a frontier settlement, and fulfill a paid contract. Local Region mission previews and site lists distinguish train-cargo hauls from resource auto-flow hauls.
- Sprint 29A/29B plus the manual playtest correction are implemented: `tutorial_six_worlds` / `tutorial_start` plus `saves/tutorial_six_worlds.json` provide a stocked six-world gate-ring tutorial start, snapshots expose backend-owned tutorial progress, and Godot renders the loop checklist, alert chip, reward context, circular galaxy layout, and click-filled one-shot dispatch setup.

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
- elemental resource catalog
- smelting, refining, manufacturing, and semiconductor chains
- power-plant and gate-energy economies
- space extraction and remote collection stations
- outpost construction by delivered cargo
- more worlds
- contracts
- corporate finance
- rival operators
- tech tree
- facility/station automation
- curved rail alignments, branches, junctions, signals, consists, and cargo wagons
- 3D facility presentation after core systems are stable
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
- `docs/construction_rules.md` is the canonical local construction rules reference for node roles, rail constraints, layout travel-time derivation, train purchase, route schedules, and deferred queue/expansion work.
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

Slice 14C completed state:
- `NodeRecipe` models per-node transformations with explicit cargo inputs and outputs.
- `apply_node_recipes` runs as a fixed tick phase after buffer distribution and before demand consumption.
- Recipes consume a full input batch or block cleanly without partial consumption when inputs are missing.
- Recipe outputs respect node storage capacity through existing inventory acceptance rules.
- Buffer distribution includes recipe input needs in a neighbour's effective pull demand, so depots and warehouses can feed industries even before declared consumer demand fires.
- Node snapshots expose recipe inputs/outputs plus per-node recipe-blocked shortfalls.
- Tests cover recipe success, missing inputs, nodes without recipes, buffer-fed recipe inputs, extractor-to-industry round trips, storage clamping, snapshot recipe fields, simulation phase ordering, and declared demand plus recipe input pull.

Slice 14D completed state:
- The Local Region `LAYERS` toggle now draws logistics overlays from backend snapshot fields: supply, demand, inventory/storage fill, node shortages, recipe-blocked inputs, and transfer pressure.
- Nodes render compact overlay badges: `S` supply, `D` demand, `I` inventory, `!` shortage, `R` recipe blocked, and `T` hot transfer.
- Transfer pressure renders as a colored ring using the same green/amber/red thresholds as the inspector; storage pressure renders as a bar under each node.
- The right HUD now includes a `Local Overlays` summary/legend with counts for supply, demand, stocked nodes, shortages, recipe stalls, and hot transfer nodes.
- No new backend schema was required; 14D consumes the snapshot contract created by 14A-14C.

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

Slice 15A completed state:
- `BuildLink` and `PreviewBuildLink` now support `mode="gate"` for explicit interworld gate links between `gate_hub` endpoints on different worlds.
- Gate-link validation rejects self-links, non-gate endpoints, same-world gate links, duplicate gate endpoint pairs, invalid capacity/travel values, invalid power sources, and insufficient cash.
- JSON command parsing supplies gate defaults when omitted: 1 travel tick, 4 slots/tick, and 80 MW.
- Gate previews return normalized build commands plus route context for UI: endpoint world names, power source, required power, available power, shortfall, and whether the link would be powered if built.
- The Local Region Gate Hub tool keeps empty-click gate-hub construction, and adds existing-gate-hub click to preview a backend gate link to an available external gate hub.
- The Gate Throughput HUD distinguishes "no gate hub", "unlinked gate hub", and linked gate states with planned slots and power draw context.
- Tests cover command defaults, preview normalization, build mutation, snapshot-powered context, invalid endpoints, same-world rejection, and power-shortfall previews.

Slice 15B completed state:
- `PreviewCreateSchedule` and `CreateSchedule` now return route gate-handoff context: `gate_link_ids`, `gate_handoffs`, and `route_warnings`.
- Gate handoffs expose endpoint world names, gate power state, power shortfall, effective slot capacity, used slots, pressure, disruption reasons, and per-gate warnings.
- Schedule previews warn when a planned route depends on saturated, hot, degraded, blocked, or unpowered gates.
- If no operational route exists because a gate is unpowered, an invalid schedule preview can still return structural gate-handoff context so the UI can explain the blocker rather than only saying "no route".
- The Local Region Build Planner renders route gate links, world handoff labels, slot pressure, power shortfalls, and warning notes for route previews.
- Tests cover normal gate handoff context, saturated gate warnings, disruption/degraded warnings, unpowered-gate invalid preview context, and create-result parity with preview context.

Slice 15C completed state:
- Local Region route creation now opens a route-tuning popup after cargo selection instead of sending fixed `units_per_departure=8` and `interval_ticks=4`.
- The popup shows train id, origin, destination, cargo, and train capacity, and lets the player set units per departure and interval ticks before backend preview.
- Schedule previews now use the tuned values and still return through the existing backend-owned `PreviewCreateSchedule` validation path.
- The Build Planner shows route tuning state while the popup is active, then shows the normalized backend command with tuned units and interval after preview.
- Backend tests lock that tuned units and interval survive preview normalization, are persisted by `CreateSchedule`, and reject non-positive or over-capacity values without mutation.
- Sprint 15's planned deliverables are now satisfied: gate-link construction, train purchase, route schedule creation, and route/gate feedback all run through backend-owned previews.

## Sprint 16: Facility Simulation Foundation

Goal:
- create the backend-owned facility layer before any station/depot/hub 3D presentation work

Deliverables:
- `Facility` model attached to `NetworkNode`
- `FacilityComponent` model for platforms, loaders, unloaders, storage bays, factory blocks, power modules, and gate interfaces
- typed `FacilityPort` inputs/outputs with cargo type, direction, rate, and capacity
- `InternalConnection` between ports
- save/load and snapshot support for facility state
- backend preview/build commands for facility components
- tests for loader rate, storage capacity, internal flow, and blocked components

Exit criteria:
- a depot or industry bottleneck can be caused and fixed by changing facility components rather than changing only local rail

## Sprint 17: Elemental Resource Backbone

Goal:
- turn the compact cargo list into a data-driven resource catalog that can support periodic-table-scale industry without making the first playable chain unmanageable

Deliverables:
- resource definitions with stable ids, display names, categories, and metadata for raw source, refined element, industrial material, manufactured good, advanced system, or exotic
- first-pass element/isotope subset covering iron, copper, aluminum, silicon, carbon, hydrogen, oxygen, lithium, cobalt, uranium, thorium, helium-3, rare earth concentrate, and selected fictional exotics
- raw deposit model for worlds and future remote sites, including grade/yield metadata
- CLI inspection/reporting for what each world or site can extract
- save/load and snapshot support for deposits and resource metadata
- rail sidecar R17: persist optional rail alignment waypoints/control points on links, expose them in snapshots, and let local rail render as curved/segmented geometry while pathfinding stays endpoint-based
- tests proving resource definitions, deposits, and snapshots remain deterministic

Exit criteria:
- a playtest can show why a world matters because of specific raw elements or deposits, not only because it has generic `ore`, and the local map can render non-straight backend-owned rail geometry

## Sprint 18: Refining and Manufacturing Chains

Goal:
- make raw extraction meaningful by adding multi-step processing from ore to refined materials, parts, electronics, semiconductors, and advanced components

Deliverables:
- smelting/refining recipes that convert raw sources into refined elements and bulk materials
- alloying/chemistry recipes that convert refined elements into industrial materials
- manufacturing recipes for parts, machinery, electronics, semiconductors, construction modules, and control systems
- facility component kinds or typed factory blocks for smelters, refineries, fabricators, electronics assemblers, and semiconductor lines
- blocked-flow reports that identify the missing material or component stage
- balanced CLI scenario proving a mine-to-smelter-to-factory chain
- rail sidecar R18: add junction/branch metadata and route-preview warnings for station throats or industry-yard pressure

Exit criteria:
- a player can improve production by connecting extraction, refining, and manufacturing nodes rather than only hauling generic cargo, with branch-heavy industry districts represented explicitly enough for future signaling

## Sprint 19: Power Plants and Gate Energy Economy

Goal:
- make gate power and industrial power depend on mined and manufactured inputs instead of mostly static world margins

Deliverables:
- power-plant models or facility components for thermal, fission, fusion, and advanced gate-support generation
- recipes for fuel, reactor fuel, coolant, reactor parts, capacitors, and gate-efficiency components
- world power capacity changes driven by operating plants and their inputs
- gate charge or gate operating-energy state tied to power infrastructure
- reports and snapshots explaining power blockers, fuel shortages, and gate operating burden
- rail sidecar R19: add stop signals, path signals, simple track blocks, and signal/block reasons in freight or traffic reports
- tests for power generation, input shortages, gate blocking, and gate recovery

Exit criteria:
- a gate route can fail or improve because the player did or did not build the upstream fuel, reactor, coolant, or capacitor chain, and dense power/gate approaches can be diagnosed through signal or block reports

## Sprint 20: Space Extraction and Collection Stations

Goal:
- let wormholes and orbital yards open access to remote resources without turning the game into a real-time piloting sim

Deliverables:
- `SpaceSite` or equivalent model for asteroid fields, moons, debris fields, gas pockets, and anomalies
- mining ships as fixed-tick logistics missions with travel time, yield, return node, fuel/power requirements, and risk hooks
- orbital yards and collection stations as logistics nodes that receive mining output
- commands/previews for starting mining missions and constructing collection stations
- CLI reports for mission status, expected return, cargo yield, and blockers
- rail sidecar R20: introduce train consists or typed capacity maps for bulk ore, liquids, protected electronics, heavy modules, reactor materials, and exotic cargo
- tests for mission dispatch, return cargo, collection-station storage, and save/load

Exit criteria:
- a player can open access to a remote ore source, send mining missions, and feed the returned material into the rail/gate industrial chain using appropriate cargo capacity or wagon types

## Sprint 21: Outpost Construction and Facility UI

Goal:
- make expansion into remote resource sites and industrial facilities diagnosable from the 2D client before any 3D work starts

Deliverables:
- outpost and ore collection station construction projects that require delivered cargo such as construction modules, machinery, power equipment, electronics, food, water, and habitat supplies
- construction progress/status reports and snapshot fields
- local node drill-in to a 2D facility detail panel or scene
- component boxes, ports, internal cargo-flow arrows, and blocked-flow readouts
- backend-preview UI for loaders, unloaders, buffers, smelters, refineries, fabricators, semiconductor lines, power modules, and gate interfaces
- local rail planning UI for curved alignments, waypoint edits, branches, signals, protected blocks, vacuum-tube portals, and consist/cargo compatibility
- overlay or inspector support for resource chain blockers and power bottlenecks

Exit criteria:
- the player can diagnose and improve a resource, manufacturing, rail, power, or outpost bottleneck through 2D backend-owned facility, track, signal, consist, and project data

## Deferred: 3D Facility View Spike

Goal:
- prove Godot can render facility snapshots in 3D without owning simulation rules after the core industry loop is stable

Deliverables:
- one 3D depot or factory scene rendered from backend facility snapshot data
- rail platform, train placeholder, loader crane, storage bay, and one processing line
- read-only first pass unless the 2D facility UI contract is stable

Exit criteria:
- the 3D scene visually matches the same backend facility state as the 2D facility view, with no simulation duplicated in Godot

## Interactive cadence

For collaborative development:

1. Pick one sprint target.
2. Break it into the next smallest testable vertical slice.
3. Implement that slice.
4. Run tests and inspect terminal output.
5. Decide whether the result is fun, clear, and extensible before expanding scope.

Slice 16A completed state:
- `Facility`, `FacilityComponent`, `FacilityPort`, `InternalConnection`, `FacilityComponentKind`, and `PortDirection` are first-class backend models attached to `NetworkNode` via the new `facility` field.
- `NetworkNode` exposes `effective_storage_capacity()`, `effective_outbound_rate()`, `effective_inbound_rate()`, and `effective_combined_rate()` that derive caps from facility components when present and fall back to the raw `storage_capacity` / `transfer_limit_per_tick` fields otherwise; `add_inventory` now respects the effective storage cap.
- A new `apply_facility_components` phase runs each tick between `node_recipes` and `node_demand`, executing FACTORY_BLOCK input→output flow with all-or-nothing input consumption. Blocked components are recorded on `state.facility_blocked` and surfaced in the per-tick report under `facilities`.
- `economy.apply_buffer_distribution` and `economy.update_transfer_saturation_streaks` now consult the effective rates, and `freight._dispatch_trip` / `_attempt_unload` cap train load and unload by the origin's outbound and the destination's inbound rates respectively.
- Snapshots expose `facility`, `facility_blocked`, `effective_inbound_rate`, `effective_outbound_rate`, `transfer_limit` (effective), `base_transfer_limit`, and `storage.{used, capacity, base_capacity}` so the Stage-2 client can render facility-derived caps without recomputing them.
- `state_to_dict` / `state_from_dict` now persist `recipe` and `facility` for every node, with helpers for ports, components, and internal connections.
- New `BuildFacilityComponent` and `PreviewBuildFacilityComponent` commands install or preview a component on a node, validate kind-specific invariants (storage_bay capacity, loader/unloader rate, factory_block inputs/outputs), reject duplicate component ids, charge `facility_component_build_cost(kind)`, and round-trip through `command_from_dict` (including ports + connections).
- 25 new tests in `tests/test_sprint16a_facility_foundation.py` cover loader-rate caps on freight load, unloader-rate caps on freight unload, storage-bay capacity overrides, fall-through to raw fields when no relevant components exist, factory-block consume/produce/blocked behavior, output clamping by effective storage cap, full simulation phase ordering, snapshot exposure, persistence round-trip, all build/preview validation rules, command JSON parsing, and the Sprint 16 exit-criterion scenario (a slow loader caps throughput; swapping it for a fast one removes the bottleneck without touching any rail link).
- Full pytest suite passes 179 tests; stdio bridge round-trip emits the new facility/effective-rate fields without regressions.

Slice 16B completed state:
- `DemolishFacilityComponent` and `PreviewDemolishFacilityComponent` remove or preview removing an existing component without charging cash.
- Component demolition rejects missing nodes/facilities/components, rejects removal while any `InternalConnection` references the component, and rejects loader/unloader removals that would reduce an active schedule endpoint below its `units_per_departure`.
- `BuildInternalConnection` / `PreviewBuildInternalConnection` validate and create port-to-port connections inside one facility, including duplicate id checks, existing endpoint checks, output-to-input direction checks, cargo compatibility checks, and one incoming connection per destination input.
- `RemoveInternalConnection` / `PreviewRemoveInternalConnection` validate and remove existing internal connections without mutating state during previews.
- Factory blocks with declared input ports now require those relevant ports to be internally wired before they can consume node inventory; removing a required connection surfaces a blocked facility entry with `reason: "open input ports"`.
- 9 new tests in `tests/test_sprint16b_facility_editing.py` cover command parsing, non-mutating previews, component removal, orphaned connection protection, active-schedule throughput protection, storage-bay capacity reclamping after demolition, connection build validation, and connection removal causing factory blockage.
- Full pytest suite passes 188 tests after the 16B facility-editing slice.

Slice 17A completed state:
- `src/gaterail/resources.py` adds a data-driven `ResourceCategory`, `ResourceDefinition`, and `ResourceDeposit` catalog separate from compact `CargoType` gameplay cargo. The first catalog covers raw sources, refined elements, industrial materials, manufactured goods, advanced systems, and undiscovered exotics.
- `GameState.resource_deposits` persists surveyed deposits with world id, resource id, grade, yield-per-tick, discovery state, and remaining-estimate metadata. Deposit validation rejects unknown worlds/resources and invalid grade/yield values.
- Built-in scenarios now seed frontier, core, and outer-world deposits such as iron-rich ore, silica sand, carbon feedstock, fissile ore, and water ice, so inspection can explain why a location matters before refining recipes exist.
- Snapshots expose top-level `resources` and `resource_deposits`, and each world includes its deposit ids. CLI/reporting adds a `resources` inspection section with deposit resource, category, grade, yield, and discovery status.
- `TrackPoint` and `NetworkLink.alignment` add backend-owned local rail geometry. Save/load and snapshots preserve alignment points, and the default scenario now includes node layouts plus curved alignment metadata for local rails.
- `BuildLink` / `PreviewBuildLink` parse `alignment`, `waypoints`, or `control_points`, reject alignment on gate links, and derive rail travel ticks from the endpoint-to-waypoint polyline when endpoint layouts are known.
- 7 new tests in `tests/test_sprint17a_resource_backbone.py` cover catalog metadata, scenario deposits, snapshot exposure, save/load persistence, CLI resource inspection, curved-link build previews, gate-alignment rejection, and model-level finite-point validation.
- Full pytest suite passes 198 tests after the 17A resource-backbone slice.

Slice 17B completed state:
- `ResourceRecipe` adds a node-owned resource transformation layer separate from cargo `NodeRecipe`, with resource-id inputs/outputs validated against the catalog.
- `NetworkNode` now supports `resource_inventory`, `resource_production`, `resource_demand`, `resource_recipe`, and optional `resource_deposit_id`, with shared storage capacity across cargo and resource units.
- `resource_chains.py` adds three fixed-tick phases: deposit/direct extraction, same-world rail-adjacent resource distribution into resource demand/recipe deficits, and resource recipe processing with all-or-nothing input validation.
- `TickSimulation.step_tick()` now runs `resource_extraction`, `resource_distribution`, and `resource_recipes` after cargo node recipes and before facility components, and emits a `resource_chains` report section.
- Sprint 8/default now includes a narrow 17B demo chain: North Ridge ore and Low Basin carbon feed Brink Ore Smelter, which makes iron, then Brink Gate Fabricator turns iron plus seeded electronics into `gate_components`.
- Persistence and snapshots now include resource inventories, resource production/demand, resource recipes, resource deposit ids, and resource recipe blockers.
- CLI `--report resources` now shows tick-level extraction, resource moves, processing output, and blockers; scenario inspection also lists resource-chain nodes and recipes.
- 5 new tests in `tests/test_sprint17b_resource_chains.py` cover extraction-to-smelting-to-gate-component output, blocker reporting/snapshots, save/load persistence, CLI resource reports, and invalid resource recipe validation.
- Full pytest suite passes 203 tests after the 17B resource-chain slice.

Slice 18 completed state:
- `ResourceRecipeKind` adds typed resource-industry roles: `generic`, `smelting`, `refining`, `electronics_assembly`, `semiconductor`, and `fabrication`.
- Resource recipes persist and snapshot their `kind`, while older saves without a kind load as `generic`.
- The default Sprint 8 playtest now has a deeper chain: iron-rich ore plus carbon becomes iron, silica plus carbon becomes silicon, copper ore becomes copper, copper plus silicon becomes electronics, electronics plus silicon becomes semiconductors, and semiconductors plus iron become gate components.
- The gate-component recipe now depends on `semiconductors` instead of seeded generic electronics, making the advanced component chain visible in blocker reports.
- `resource_branch_pressure(state)` identifies dense local resource rail clusters and reports node degree, severity, recipe kind, involved links, and neighbours.
- Snapshots expose top-level `resource_branch_pressure`; CLI `--report resources` shows branch-pressure warnings in both tick reports and scenario inspection.
- 5 new tests in `tests/test_sprint18_resource_industry.py` cover typed recipe metadata, silicon/electronics/semiconductor flow, gate-component output, branch-pressure snapshots/reports, CLI resource inspection, and legacy save compatibility.
- Full pytest suite passes 208 tests after the Sprint 18 typed-industry slice.

Slice 19 completed state:
- `GatePowerSupport` adds a resource-chain gate support model keyed to one gate link and one support node, with required resource inputs, active state, and a power-bonus value.
- `GameState.add_gate_support()` validates target gate links, endpoint-world support nodes, positive resource inputs, positive power bonus, duplicate support ids, and duplicate supports for one gate.
- Gate evaluation now applies available resource support as an effective power-draw reduction while preserving the base link power requirement. Missing support resources surface as gate support shortages instead of silently behaving like static world power.
- `GatePowerStatus` now records base power required, effective power required, resource power bonus, support id/node, support inputs, and support missing resources.
- Persistence, snapshots, and tick reports now include gate support data. Link snapshots expose `effective_power_required` and `gate_support`, and gate reports describe whether a gate is waiting on resources or supported by a node.
- New `sprint19` / `power` / `gate_power` scenario lowers Brink Frontier's static power margin and adds a gate-component support rule for `gate_frontier_outer`, so the gate remains underpowered until the Sprint 18 chain fabricates `gate_components`.
- 5 new tests in `tests/test_sprint19_gate_power_resources.py` cover resource-gated power recovery, support persistence/snapshots, CLI report text, non-gate validation, and unknown resource validation.
- Full pytest suite passes 213 tests after the Sprint 19 resource-backed gate-power slice.

Sprint 19B / 20A power-generation foundation completed state:
- `PowerPlantKind` and `PowerPlant` add backend-owned thermal/fission/fusion generation metadata attached to a logistics node, with resource inputs, output, active state, and validation for node ownership and resource ids.
- `WorldState.power_generated_this_tick` separates generated power from static `power_available`, and `base_power_margin` now includes generated power before gate reservations.
- `power.apply_power_plants()` runs before `gate_power`, consumes required resource inputs, records missing-input blockers, and adds generated power to the owning world for the current tick.
- The `sprint19b` / `power_generation` scenario adds a carbon-fed thermal plant that raises Brink Frontier's effective power enough to run `gate_frontier_outer`.
- Save/load, snapshots, scenario inspection, tick reports, and CLI `--report power` now expose power plants, generated power, input consumption, and plant blockers.
- 5 new tests in `tests/test_sprint19b_power_generation.py` cover generated power gating, missing-input blockers, persistence/snapshots, validation, and CLI power/gate reporting.
- Full pytest suite passes 224 tests after the power-generation foundation slice.

R19 rail sidecar first-slice completed state:
- `TrackSignalKind` and `TrackSignal` add backend-owned stop/path signal metadata on rail-link endpoints, with validation that signals only protect rail links and optional signal nodes are link endpoints.
- Active signals now turn a rail link into a protected block. Freight dispatch checks those blocks inside the existing route-capacity reservation path before loading cargo, so blocked trains queue without consuming inventory.
- The first block model is intentionally conservative: one signaled link is one block, and in-transit trains keep that block occupied until arrival. Junction/path routing depth remains a future slice.
- `BuildTrackSignal` and `PreviewBuildTrackSignal` expose signal placement through the JSON command surface, and demolition refuses links that still own track signals.
- Save/load, render snapshots, scenario inspection, tick reports, traffic alerts, and freight queued events now expose signal ids, protected blocks, occupiers, reservations, and signal-block reasons.
- 6 new tests in `tests/test_sprint19_signals_blocks.py` cover signaled block queueing, unchanged unsignaled capacity behavior, in-transit occupancy, command/persistence/snapshot contracts, text reporting, and non-rail validation.
- Full pytest suite passes 219 tests after the R19 signal/block sidecar slice.

Sprint 21C map/wiki foundation completed state:
- `godot/scripts/local_region.gd` now makes node and gate-hub placement snap explicit in the 2D local map: empty gate-hub placement uses the snapped coordinate, the snap cursor highlights the active 24-unit grid cell, and the build planner/status chip show the grid rule.
- `docs/resource_relationship_atlas.md` adds a text-first relationship atlas for raw sources, processors, assemblers, power plants, gate support, gate links, spaceports, and remote extraction sites. This replaces the requested HTML page to respect the repository rule against browser interfaces.
- The atlas is hand-authored for this slice and marks a later CLI-generated catalog as the natural follow-up.

Sprint 21D internal wiring completed state:
- Facility components now own per-port cargo buffers, and internal connections move cargo from source output ports or shared facility stock into specific destination input ports before factory processing.
- Factory blocks with input ports consume from those wired port buffers; legacy factory blocks without ports still use node inventory directly.
- Factory output ports can buffer produced cargo and push it through downstream internal connections in the same tick, while full output ports block the component without consuming inputs.
- Save/load and render snapshots include port inventory, so the client can show where cargo is stuck inside a facility.
- The Godot Local Region adds a Wire Ports tool and a selected-node facility drill-in panel that renders components, ports, existing internal wires, drag-to-connect preview lines, port inventories, and blocked components.
- 4 new tests in `tests/test_sprint21d_internal_wiring.py` cover wired input transfer, output transfer, full-output blockers, persistence, and snapshot exposure.
- Full pytest suite passes 230 tests after the 21D internal-wiring slice.

Sprint 22 completed state:
- directional gates now distinguish source and exit endpoints while preserving bidirectional legacy gates.
- reciprocal one-way gate links are allowed, but duplicate same-direction links are rejected.
- train consists are validated at purchase, schedule preview/create, and runtime dispatch, with specialized cargo reporting the required consist.
- tests cover directional route availability, reverse-link metadata, consist parsing, preview validation, matching specialized schedules, and runtime blocking.

Sprint 23 completed state:
- schedules support ordered intermediate `stops`.
- preview/create results include exact `route_stop_ids`, route segments, route nodes/links, gate handoff context, and structural blockers for invalid operational routes.
- command parsing, save/load, snapshot output, dispatch route use, and CLI inspection preserve multi-stop services.

Sprint 24 completed state:
- snapshots expose `cargo_flows` for schedule services.
- each flow includes schedule identity, cargo, active state, configured stop sequence, resolved route nodes/links, trip counters, delivered units, and in-transit units.
- Godot draws cargo-flow overlays from snapshot payloads instead of inferring flow rules client-side.

Sprint 25 completed state:
- `PreviewUpdateSchedule` / `UpdateSchedule` edit existing schedules through the same backend-owned route, stop, consist, and next-departure validation used by schedule creation.
- `PreviewDeleteSchedule` / `DeleteSchedule` remove idle schedules and reject schedules with an active in-flight schedule trip.
- schedule snapshots include `priority` and `return_to_origin`, and schedule deletion removes the related cargo-flow payload.
- Godot bridge helpers and main-panel controls let the player preview/apply schedule cargo, units, interval, active-state, and intermediate-stop edits, then delete idle schedules.
- invalid schedule edit previews surface route-segment and blocked-link reasons in the status strip.

Sprint 26 completed state:
- the stdio bridge accepts `save_path`, `load_path`, and `scenario` frames, replacing the live Python simulation in-place and returning `saved_path`, `loaded_path`, or `loaded_scenario` metadata in the bridge payload.
- `early_build` / `early` / `starter` / `new_game` adds a sparse two-world start with limited cash, construction stock, one starter train, and one inactive starter schedule for first-build testing.
- `industrial_expansion` / `industrial` / `expanded` / `large_industry` adds a larger connected web with extra worlds, gates, resource deposits, typed industries, power plants, gate support, and multi-stop services for stress testing industry logistics.
- the Godot bridge exposes save/load/scenario helpers, and the Galaxy Map control panel has a save path field, Save Game, Load Game, and scenario reset controls.
- tests cover bridge save/load round-trip, bridge scenario reset, scenario catalog listing, preset scale/content expectations, and Godot script wiring.

Sprint 27 completed state:
- mining mission previews and dispatches now use backend-computed fuel and power requirements from the selected `SpaceSite`; omitted client fields no longer allow free launches.
- mission previews report invalid sites, bad launch/return node kinds, missing fuel, power shortfall, expected yield, return capacity, and the normalized dispatch command.
- dispatched missions consume fuel, reserve world power, release reserved power on completion/failure, and return resources into collection/orbital storage for the existing resource-distribution and recipe phases to consume on later ticks.
- outpost bootstrap remains backend-owned: preview/build stage an outpost construction project, delivered cargo completes it, and completion promotes the node into an operational logistics role.
- Local Region now previews mining missions from spaceport nodes, shows fuel/power/yield/return-space context from backend command results, and only dispatches after preview confirmation.
- tests cover backend-computed requirements, missing-fuel blockers, returned resources feeding local industry, legacy space lifecycle persistence, and Local Region preview wiring.
- `SpaceSite.cargo_type` (optional `CargoType`) lets a site return its haul into `node.inventory[cargo_type]` (the train-cargo bucket) instead of `node.resource_inventory[resource_id]`. When set, mission completion reports the haul under `space_missions.returned_cargo` keyed by cargo value; sites without a `cargo_type` keep the existing resource-id auto-flow path. The new field round-trips through persistence and snapshot.

## Sprint 28: Mining-To-Manufacturing Gameplay Loop

Goal:
- close the headline gameplay loop in a single playable scenario: dispatch a mining mission, watch it return cargo into a collection station, schedule trains to ferry that cargo through a gate, smelt/build it into useful parts, deliver those parts to a settlement, and receive contract rewards for future expansion.

Deliverables:
- a new scenario preset that demonstrates the closed loop end-to-end and is fully exercised by automated tests.
- Local Region UI surfaces whether each `SpaceSite` returns into the train-cargo bucket (`cargo_type` set) or the resource-id auto-flow bucket, so the player can predict the haul's destination before dispatch.
- A bridged "queue mining run" UX in Local Region that sequences `DispatchMiningMission` and (optional) schedule activation without leaving the panel.
- Cargo-flow overlay/alert support for the new haul services so the live train loop is legible from the map.

Slice progress:
- 28A complete: backend scenario `mining_to_manufacturing` / `mining_loop` plus end-to-end pytest for mission -> cargo haul -> smelter -> fabrication -> PARTS.
- 28B complete: command previews return `site_cargo_type`, `site_resource_id`, `haul_bucket`, and `haul_label`; Local Region preview/site catalog renders cargo vs resource bucket badges.
- 28C backend payoff complete: the scenario includes `frontier_settlement`, `parts_to_frontier_settlement`, and `frontier_parts_upgrade`, proving manufactured PARTS can satisfy settlement delivery contracts and pay cash/reputation rewards.
- sync hardening complete: snapshots expose backend-owned `scenario_catalog` and `cargo_catalog`; Godot uses those payloads for scenario and cargo selectors instead of duplicating Python registries.
- 28C Godot workflow remaining: Local Region one-click "schedule the haul run" flow tied to the dispatched mission's expected return tick / cargo.
- 28D remaining: bridge cargo-flow overlays + alert chips reflect the haul and settlement-delivery services so the player can monitor the loop visually.

Exit criteria:
- a player loads the scenario, dispatches one mission, activates the haul and settlement delivery schedules, and watches the settlement contract pay out without manually editing state; the same loop runs deterministically under pytest.

## Deferred (post-Sprint 28)

- Local Region rail/signal planning controls for backend-owned alignments and track signals (preview waypoint edits, signal placement, protected block warnings, consist/cargo compatibility). Previously slotted as Sprint 28; deferred behind closing the mining-to-train gameplay loop.

3D facility presentation should still wait until after resource, power, space-extraction, outpost, rail-depth, and 2D diagnostic contracts are stable.

## Sprint 29: Tutorial Start And UI Loop Polish

Goal:
- make the real loop approachable from a generous starting state.

Completed 29A state:
- `tutorial_six_worlds` / `tutorial_start` creates six worlds in a powered ring.
- every world has two gate neighbours, local depots, stocked construction inventory, settlements, and gate hubs.
- tutorial schedules move ORE from Brink Mines to Cinder Forge, METAL from Cinder Forge to Atlas Yards, and PARTS from Atlas Yards to Helix Reach.
- the Helix starter contract pays cash/reputation once PARTS arrive.
- `saves/tutorial_six_worlds.json` is generated from the scenario for immediate save/load testing.

Completed 29B state:
- `render_snapshot()` emits a `tutorial` payload for the six-world starter loop, including step status, cargo progress, rewards, alerts, and the next backend action.
- Godot's main view renders that payload as a Tutorial Loop checklist without hardcoding tutorial schedule IDs or logistics rules.
- the tutorial alert appears in the status chip strip alongside bridge, route, disruption, and congestion alerts.

Manual playtest correction:
- tutorial schedules now start disabled, so pressing Play no longer completes the loop automatically.
- the six tutorial worlds render in a backend-owned circular galaxy layout instead of a straight line.
- the Galaxy Map one-shot dispatch form is click-filled from map selection: select a train, select a pickup node, select a dropoff node, then queue the order.
- backend tests prove the loop can be completed by manual one-shot orders before the player later chooses to automate routes with schedules.
