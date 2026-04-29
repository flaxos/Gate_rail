---
spec_id: sprint20bc-21c
title: Sprint 20B/C Space-Extraction Loop Closure & Sprint 21C Diagnostic Overlays
version: 1.0.0
status: draft
satisfaction_target: 0.85
holdout_ratio: 0.20
created_at: 2026-04-29
authors:
  - octo:spec session, gate_rail repository
related_docs:
  - docs/facility_layer_plan.md
  - docs/construction_rules.md
  - PHASE2_PLAN.md (Sprint 20 + Sprint 21)
  - GAME_VISION.md (space extraction, outposts)
  - DESIGN_NOTES.md (space extraction layer)
  - specs/sprint16-polish.nlspec.md (predecessor — facility kinds + block reasons)
---

# Sprint 20B/C Space-Extraction Loop Closure & Sprint 21C Diagnostic Overlays

## 1. Purpose

Sprint 20A is shipped: `SpaceSite`, `MiningMission`, `MiningMissionStatus`, `DispatchMiningMission` / `PreviewDispatchMiningMission` commands, and `advance_mining_missions` tick phase. Sprint 16C polish landed in PR #10 with 12 specialized facility component kinds and structured `FacilityBlockReason`. Sprint 21D shipped internal facility wiring + 2D drill-in.

What's missing is the **loop closure**: mining missions currently drop resources at any return node (no specialization, no capacity constraint, no fuel/power consumption), there is no outpost-construction workflow that requires delivered cargo before a frontier site becomes operational, and the facility-block / power-shortfall / resource-shortage diagnostics introduced in Sprint 16C/19/19B are not yet rendered as Local Region overlays.

This spec bundles three slices:

- **20B** — orbital infrastructure (`OrbitalYard` / `CollectionStation` node kinds), mining-mission resource consumption (fuel/power), and return-capacity respect.
- **20C** — outpost construction workflow that reuses existing `ConstructionProject` machinery: `BuildOutpost` / `PreviewBuildOutpost`, cargo-driven activation, completion unlocks the outpost as a valid mission launch / route endpoint.
- **21C** — diagnostic overlays in the Local Region scene that consume backend snapshot fields for resource shortages, processing blockers, power shortfalls, and outpost-construction progress.

Together they let the player run a recursive expansion loop: mine remote site → return to collection station → train through facility chain → manufacture construction modules → deliver to outpost site → outpost goes operational → opens new mining-mission launch point or gate-link endpoint.

## 2. Actors

- **Player** — places an orbital yard or collection station, dispatches mining missions through it, builds an outpost project that consumes delivered cargo, and reads the new overlays to diagnose where production is stuck.
- **Backend simulation** — owns node-kind capabilities, mission resource consumption, mission return-capacity enforcement, outpost-project state machine, and the diagnostic snapshot fields the overlays render.
- **JSON bridge** — relays new construction commands and exposes new snapshot fields. Backwards-compatible with existing Sprint 20A consumers.
- **Godot Local Region scene** — adds outpost placement tool, mining-mission queue panel, and 21C overlay layers (purely presentation).
- **CLI playtester** — `gaterail --inspect --report space,outposts` should remain readable.

## 3. Existing Foundation (DO NOT re-implement)

Already shipped:

- `MiningMissionStatus` (preparing / en_route / mining / returning / completed / failed) — `src/gaterail/models.py`.
- `SpaceSite` (id, name, resource_id, travel_ticks, base_yield, discovered) — `src/gaterail/models.py`.
- `MiningMission` (id, site_id, launch_node_id, return_node_id, status, ticks_remaining, fuel_input, power_input, expected_yield) — `src/gaterail/models.py`.
- `DispatchMiningMission`, `PreviewDispatchMiningMission` — `src/gaterail/commands.py`.
- `advance_mining_missions(state)` tick phase — `src/gaterail/space.py`.
- `ConstructionStatus` (PENDING / ACTIVE / COMPLETED) and `ConstructionProject` (target_node_id, required_cargo, delivered_cargo, status) — `src/gaterail/models.py`. Generic project machinery already exists; reuse it.
- `apply_construction_projects(state)` cargo-pull tick phase — `src/gaterail/construction.py`.
- `NodeKind.SPACEPORT` (cost 3000, storage 2000, transfer 24) — already in `NODE_BUILD_COST`.
- `FacilityBlockReason` enum + `facility_block_entries` snapshot — Sprint 16C, PR #10.
- Sprint 14D `LAYERS` toggle for supply / demand / inventory / shortages / recipe_blocked / transfer_pressure.

Treat these as canonical. Do not rename, remove, or duplicate them. New kinds and commands extend the existing surface.

## 4. In-Scope Behaviors

### B1. Orbital infrastructure node kinds

Add two `NodeKind` entries to `src/gaterail/models.py`:

| Kind | String | Role |
|---|---|---|
| `ORBITAL_YARD` | `orbital_yard` | Deep-space hub: builds and dispatches mining ships, consumes fuel + power per mission |
| `COLLECTION_STATION` | `collection_station` | Receives mission cargo, transfers into rail/gate logistics — high storage, modest transfer |

Each new kind must have a default cash cost (suggested: orbital_yard 6000, collection_station 4000), default storage capacity (orbital_yard 3000, collection_station 5000), default transfer-per-tick (orbital_yard 24, collection_station 36), and an entry in `NODE_BUILD_CARGO` requiring delivered modules (e.g. orbital_yard requires `construction_materials: 200, electronics: 50, machine_parts: 50`; collection_station requires `construction_materials: 250, machine_parts: 30`).

`SPACEPORT` is preserved unchanged — it remains a generalist surface launch site. The new kinds are specialized.

**Rule:** `MiningMission.launch_node_id` must reference a node whose kind is `ORBITAL_YARD` or `SPACEPORT` (other kinds rejected at preview/dispatch). `MiningMission.return_node_id` must reference a node whose kind is `COLLECTION_STATION`, `ORBITAL_YARD`, `SPACEPORT`, or `WAREHOUSE` (other kinds rejected).

### B2. Mining missions consume fuel + power; respect return-capacity

`advance_mining_missions` currently never consumes `fuel_input` or `power_input`. Lock the following on dispatch:

- `PreviewDispatchMiningMission` checks that the launch node has `≥ fuel_input` of cargo type `fuel` (use a stable cargo identifier — confirm what already exists in `cargo.py` and reuse) and `≥ power_input` of available world power. Returns ok=false with a structured reason when short.
- `DispatchMiningMission` deducts `fuel_input` from launch-node inventory and reserves `power_input` from the launching world's `power_used` for the mission's lifetime (deterministic, persisted on the mission).
- On `COMPLETED`, the reserved power is released (added back to world `power_available` accounting in the next tick). On `FAILED`, fuel is forfeit; reserved power is also released.
- `advance_mining_missions` enforces **return capacity**: when delivering cargo to `return_node`, the amount actually accepted is capped at `node.effective_storage_capacity() - node.total_inventory()`. Surplus is **lost** for now (logged in the tick result as `mission_id, dropped_units` — no rerouting). v1 only.
- Per-tick power upkeep beyond `power_input` is out of scope.

### B3. Outpost construction projects

Reuse `ConstructionProject` for outposts. Add:

- `OutpostKind` enum: `OUTPOST_FRONTIER` (default), `OUTPOST_RESEARCH`, `OUTPOST_MINING_HUB`. Each has required_cargo defaults defined in `construction.py` (`OUTPOST_BUILD_CARGO`).
  - `OUTPOST_FRONTIER`: construction_materials 300, electronics 80, food 200, water 200, power_cells 40
  - `OUTPOST_RESEARCH`: construction_materials 250, electronics 200, machine_parts 60, semiconductors 30
  - `OUTPOST_MINING_HUB`: construction_materials 350, machine_parts 120, electronics 80, fuel 100
- New commands: `BuildOutpost`, `PreviewBuildOutpost`, `CancelOutpost`, `PreviewCancelOutpost`. `BuildOutpost` creates a `ConstructionProject` with `status = PENDING` and a placeholder `NetworkNode` of kind `OUTPOST_FRONTIER` etc. (or reuse `EXTRACTOR` with a flag — pick the cleanest in v1; the spec prefers a dedicated `OUTPOST` kind below).
- Add `NodeKind.OUTPOST` (string `outpost`) for the placeholder node. `NetworkNode.outpost_kind: OutpostKind | None` distinguishes variant.
- `apply_construction_projects` already pulls cargo into `delivered_cargo`. Extend so when `delivered_cargo == required_cargo`, status flips to `COMPLETED` and the node's `kind` is **promoted** from `OUTPOST` to whatever the variant unlocks (frontier → `EXTRACTOR`, research → `INDUSTRY`, mining_hub → `ORBITAL_YARD`). Promotion is deterministic.
- An `OUTPOST` node (status `PENDING` or `ACTIVE`) cannot be a route endpoint, mission launch, or mission return. It can receive cargo deliveries (the construction project pulls from inventory).
- A `COMPLETED`-promoted node functions as its promoted `NodeKind`.

### B4. Cancel & refund

- `CancelOutpost` removes the placeholder node and the `ConstructionProject`, refunds 50% of cash and 50% of cargo already delivered to a chosen refund node (default: nearest `WAREHOUSE` or `DEPOT` on the same world, fail to ok=false if none exists).
- `PreviewCancelOutpost` returns the planned refunds without mutation.

### B5. Snapshot completeness for outposts and missions

Extend `render_snapshot()`:

- Per outpost: `{ "id", "kind", "outpost_kind", "construction_status", "required_cargo", "delivered_cargo", "remaining_cargo", "progress_fraction" }`.
- Per mission: keep current fields, add `"reserved_power"`, `"fuel_consumed"`, `"projected_yield"` (= `expected_yield`, but renamed for clarity in the snapshot — keep the model field name unchanged).
- Top-level `outposts: [...]` array sorted by id.
- Top-level `mining_missions: [...]` array sorted by id (already exists; verify and extend).

Bridge errors must remain non-fatal: invalid build outpost commands return ok=false with structured reason codes (e.g. `unknown_outpost_kind`, `missing_layout`, `world_not_found`, `insufficient_cash`).

### B6. Sprint 21C diagnostic overlays

Sprint 14D added `LAYERS` toggle with: supply, demand, inventory/storage_pressure, shortages, recipe_blocked, transfer_pressure. Sprint 16C added `facility_block_entries`. Sprint 19/19B added power data. Sprint 21C exposes them as overlay layers in the Local Region scene.

Add to the existing `LAYERS` dropdown three new layers:

- **`facility_block_layer`** — overlays facility-blocked components from `facility_block_entries` keyed on node id. Color by reason: `MISSING_INPUTS` red, `OPEN_INPUT_PORTS` amber, `OUTPUT_PORTS_FULL` cyan, `NODE_STORAGE_FULL` magenta, `POWER_SHORTFALL` red. Hover/select shows the structured detail.
- **`power_layer`** — overlays world-level `power_available` / `power_used` deltas, gate hub power draw, and node-attached power-plant generation. Reads `world.power_available`, `world.power_used`, `node.power_provided`, `node.power_required` from snapshot. No new backend behavior — purely a render path over existing fields.
- **`outpost_layer`** — overlays `OUTPOST` placeholder nodes with progress rings (fraction `delivered/required`), construction status badge, and a per-cargo bar list (top 3 most-needed cargo types). Reads from the new `outposts: [...]` snapshot array.

Backend exposure:

- All overlay data must be available in `render_snapshot()` without further commands.
- Overlay-eligible nodes carry an `overlay_pip` summary in the snapshot (`{"layer": <layer-id>, "severity": "info"|"warn"|"error", "label": <short-string>}`) so Godot can draw a single map-level pip without computing per-layer logic.
- Existing overlay layers (Sprint 14D) continue to function unchanged.

### B7. JSON bridge contract additions

- `PreviewBuildOutpost` / `BuildOutpost` accept `{ "world_id", "outpost_kind", "layout": {"x", "y"}, "world_id" }`. Returns `{"ok", "message", "cost", "cargo_required", "duration_estimate_ticks", "normalized_command"}`. Cost defaults from `OUTPOST_BUILD_COST` constants.
- `PreviewCancelOutpost` / `CancelOutpost` accept `{ "outpost_id" }`. Returns refund preview.
- `PreviewDispatchMiningMission` extends current response to include `fuel_required`, `fuel_available`, `power_required`, `power_available`, `power_shortfall_if_dispatched`, `return_capacity_estimate`.
- `BridgeError` codes for these new commands follow the existing structured-result pattern (no top-level errors).

### B8. CLI parity

`gaterail --inspect --report space` must list:

- All `SpaceSite`s with id, name, resource_id, travel_ticks, base_yield, discovered.
- All active `MiningMission`s with id, status, ticks_remaining, launch/return nodes, expected_yield, reserved_power, fuel_consumed.
- All `OUTPOST` nodes with kind, status, progress %, top-3 most-needed cargo.

`gaterail --inspect --report outposts` is an alias filter for the outpost subset.

## 5. Constraints

- **Determinism**: identical state + identical commands produce identical snapshots, ticks, and resource flows.
- **Save compatibility**: existing Sprint 20A saves must load. New fields default safely. New `NodeKind` entries do not collide with existing string values.
- **Backward bridge compatibility**: existing JSON commands continue to work unchanged. New fields are additive. `SNAPSHOT_VERSION` stays at its current value unless a key is renamed.
- **Test discipline**: every behavior in §4 needs ≥1 pytest. Godot UX gets a smoke note in `PHASE2_PLAN.md`.
- **Layer purity**: simulation rules in `gaterail.space` / `gaterail.construction`. Godot reads, does not derive logic.
- **Cost discipline**: only the listed new node kinds, commands, and overlay layers. No tech tree, contracts, rival operators, market pricing, mission-route reservation between worlds, or signal extension to space lanes.
- **Power accounting**: power reservation for missions must integrate cleanly with the existing facility power accounting from Sprint 16C/19B. No double-counting.
- **Time for outposts**: cargo delivery drives progress. No real-time construction tick beyond `apply_construction_projects` cargo pull (already in place). Delayed/timed construction beyond cargo delivery remains deferred.

## 6. Acceptance Criteria

First 80% drive embrace; last 20% reserved as holdout.

### AC1 — Orbital yard / collection station kinds installable
- Build an `ORBITAL_YARD` via `BuildNode(kind="orbital_yard", ...)` with required cargo on hand. Node appears, snapshot reports `kind: orbital_yard`, default storage 3000, default transfer 24.

### AC2 — Mining mission requires valid launch / return kinds
- `PreviewDispatchMiningMission` with `launch_node_id` referencing a `SETTLEMENT` returns `ok: false, reason: invalid_launch_kind`.
- Same with `return_node_id` referencing an `INDUSTRY`: `ok: false, reason: invalid_return_kind`.
- `ORBITAL_YARD` launch + `COLLECTION_STATION` return is accepted.

### AC3 — Mining mission consumes fuel
- Launch node has 100 fuel. Mission requires 30 fuel. Dispatch. Launch node has 70 fuel afterward.
- Retry with 20 fuel and 30 required: preview returns `ok: false, reason: insufficient_fuel`. Dispatch is rejected.

### AC4 — Mining mission reserves power for its lifetime
- World power_available 200, power_used 50. Mission requires 30 power. Dispatch. World power_used = 80 while mission is in flight.
- On COMPLETED, power_used returns to 50.

### AC5 — Mining mission return capped by storage
- Mission `expected_yield = 500`. Return node has 200 free storage. Tick to completion. Node stock increases by 200; tick result includes `dropped_units = 300`.

### AC6 — BuildOutpost stages a placeholder node
- `PreviewBuildOutpost(outpost_kind="outpost_frontier", world_id="w1", layout={x:100, y:100})` returns `ok: true, cost`, `cargo_required` matching `OUTPOST_BUILD_CARGO[OUTPOST_FRONTIER]`.
- Commit. A new node appears with `kind: outpost`, `outpost_kind: outpost_frontier`, construction_project with `status: PENDING` and `required_cargo` populated.

### AC7 — Cargo delivery promotes outpost on completion
- Outpost has required `construction_materials: 100`. Deliver 100 construction_materials to the node. Tick. After `apply_construction_projects` runs:
  - Construction project `status: COMPLETED`.
  - Node `kind` changes from `OUTPOST` to `EXTRACTOR` (per `OUTPOST_FRONTIER` promotion rule).
  - Node is now a valid route endpoint and a valid mining-mission launch (frontier promotes to extractor, not orbital_yard — adjust expectation if implementer picks different mapping; document in §8).

### AC8 — In-progress outpost rejects route endpoint
- Build a `BuildLink` rail between an existing depot and an `OUTPOST` placeholder. Preview: `ok: false, reason: outpost_not_operational`.

### AC9 — Cancel outpost refunds 50%
- Outpost has 600 cash spent + 50 construction_materials delivered. Cancel via `CancelOutpost`. Cash refund: 300. Construction_materials returned to refund node: 25 (rounded down).
- Construction project removed; placeholder node removed.

### AC10 — Snapshot exposes outpost progress
- Three outposts at 0%, 33%, 100% (the last just promoted). Snapshot top-level `outposts: [...]` includes each with progress_fraction = 0.0, 0.33333, 1.0 respectively (last shows promoted kind alongside).

### AC11 — Snapshot exposes mission reserved_power and fuel_consumed
- Mission with `fuel_input=30, power_input=15` in `EN_ROUTE` state: snapshot mission entry shows `reserved_power: 15, fuel_consumed: 30`.

### AC12 — Save round-trip through outpost lifecycle
- Build outpost, deliver 50% of required cargo, save. Load. Tick to completion. State is identical to a path that never saved (assert via `state_to_dict` round-trip equality on a sorted JSON dump).

### AC13 — Bridge handles unknown outpost_kind gracefully
- `PreviewBuildOutpost(outpost_kind="not_real")` returns `command_results[0] = {"ok": false, "reason": "unknown_outpost_kind"}`. No top-level error.

### AC14 — facility_block_layer overlay snapshot fields
- Snapshot contains `overlay_pip` on a node whose facility has a blocked component with `reason: "missing_inputs"`. Pip `severity: "warn", label: "missing inputs"`.

### AC15 — power_layer overlay reads existing fields
- World with `power_used > power_available - 10` (near deficit). Snapshot exposes `world.power_pressure: float` (or equivalent), and at least one node with `power_required > 0` carries an `overlay_pip` for the power layer.

### AC16 — outpost_layer overlay surfaces top-3 needs
- Outpost with cargo needs `construction_materials: 200` (delivered 50), `electronics: 80`, `food: 200`, `water: 200`, `power_cells: 40`. Snapshot's outpost entry includes a `top_needs: [...]` array of the three highest remaining (likely water, food, construction_materials in some order).

### AC17 — CLI inspector lists outposts
- `gaterail --inspect --report outposts` on a state with two PENDING outposts and one COMPLETED outpost prints id, kind, status, progress, top-3 needs in stable sort order. COMPLETED outposts list as `(active)` with their promoted kind.

### AC18 (holdout candidate) — Mission failure releases reserved power and forfeits fuel
- Mission with `fuel_input=30, power_input=15` mid-flight. Force `status: FAILED` (e.g. via test hook or by deleting the SpaceSite). Tick: world power_used drops by 15, launch-node fuel inventory remains 30 lower than pre-dispatch.

### AC19 (holdout candidate) — Recursive expansion loop end-to-end
- Scenario: frontier world has one extractor + one orbital yard. Dispatch mining mission to a SpaceSite. Mission returns 200 mixed_ore to a collection station. Train hauls ore to a smelter facility (Sprint 16C kind). Smelter produces metal. Fabricator produces construction_materials. Build a new outpost project on a remote world. Train delivers construction_materials to outpost. Outpost completes and promotes. Verify the promoted node can be used as the launch_node for a new mining mission.

### AC20 (holdout candidate) — Save/load mid-construction round-trip determinism
- Two parallel simulations from the same initial seed. Both build the same outpost, deliver the same partial cargo, save, load on the other side, complete delivery, tick to promotion. Final `state_to_dict()` outputs are byte-equal.

### AC21 (holdout candidate) — Cancel during partial delivery deterministic refund
- Outpost requires 100 cm + 80 electronics. Deliver 60 cm + 50 electronics. Cancel. Refund: 30 cm + 25 electronics + 50% of cash. Run twice, refunds identical.

### AC22 (holdout candidate) — Godot overlay regression smoke (manual)
- Manual playtest note: in Local Region, build an outpost, watch progress ring fill from 0 → 100%, verify outpost_layer pip color shifts as cargo arrives, verify facility_block_layer pip appears on a smelter starved of input, verify power_layer pip lights when a mining mission reserves power that pushes the world into deficit.

## 7. Out of Scope

- Real-time per-tick mining (missions are fixed-tick only).
- Mission rerouting on failure or storage overflow.
- Outpost re-specialization after promotion.
- Tech tree, market pricing, contract authoring, rival operators, advanced finance.
- Per-tick mission power upkeep (only entry-time reservation).
- New cargo types beyond what already exists in `cargo.py`.
- Curved alignments / signals / consists / wagons (Sprint 21E scope).
- 3D facility view.
- New world creation. Outposts are placed on existing worlds only.
- Multi-stage construction queues (delayed build jobs remain deferred).

## 8. Open Questions / Risks

- **Promotion mapping**: `OUTPOST_FRONTIER → EXTRACTOR`, `OUTPOST_RESEARCH → INDUSTRY`, `OUTPOST_MINING_HUB → ORBITAL_YARD` is the v1 mapping. If implementer prefers preserving `OUTPOST` kind permanently with an `outpost_active: bool` flag, document the deviation. Either is acceptable as long as B3 promotion semantics hold.
- **Fuel cargo identifier**: spec assumes a `fuel` cargo type exists; verify in `cargo.py` and use the canonical name. If only `fuel_oil` / `volatiles` exist, pick the closest and document.
- **Power accounting double-count**: Sprint 16C added `power_provided`. Mining mission power reservation must integrate with the same world `power_used` accounting; verify no path adds a mission's reservation twice (once on dispatch, once via facility tick).
- **Outpost kind on a remote world**: outposts are usually placed on under-developed frontier worlds. Verify there's nothing in `WorldState` that prevents `BuildOutpost` from targeting a tier-0 outpost world.
- **Refund node selection**: "nearest warehouse or depot on the same world" is heuristic; if no rail-connected warehouse exists, fail to ok=false. Document the picker tie-break (lowest layout-distance, then lowest id).
- **Overlay data volume**: snapshot size grows per overlay. If concerns arise, gate overlay payloads behind a `request_overlays: true` query field on the bridge. Default behavior in v1: always include.

## 9. Glossary

- **OrbitalYard**: deep-space hub for mining mission dispatch.
- **CollectionStation**: high-storage node specialized to receive mining mission output.
- **Outpost**: placeholder construction project that promotes to a real node kind once cargo delivery is complete.
- **Promotion**: deterministic transition from `OUTPOST` to a target `NodeKind` upon construction completion.
- **Reserved power**: power_used delta tracked against a world for a mission's lifetime, released on `COMPLETED` or `FAILED`.
- **Overlay pip**: a single per-node summary the Local Region scene uses to render layered diagnostics without computing logic Godot-side.

---

## Spec Self-Adversarial Notes

Local pre-embrace adversarial pass:

1. **Promotion model ambiguity** — flagged in §8.
2. **Power double-count risk** — flagged in §8 + AC4 explicitly checks accounting.
3. **Refund picker non-determinism** — pinned by tie-break in §8.
4. **Outpost vs route endpoint** — AC8 locks the rejection path.
5. **Fuel cargo identifier missing in cargo.py** — flagged in §8.
6. **Snapshot size growth from overlays** — flagged in §8 with a deferable opt-in path.
7. **No new cargo types** — explicit in §7 Out of Scope.
8. **Holdout coverage**: AC18-AC22 cover failure paths, end-to-end loop, save round-trip, cancel determinism, and a manual UX smoke — diverse holdout slice.
