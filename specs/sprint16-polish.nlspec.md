---
spec_id: sprint16-polish
title: Sprint 16 Polish & Sprint 21B Component Build-Preview UX
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
  - PHASE2_PLAN.md (Sprint 16 + Sprint 21)
  - PHASE2_UI_WIREFRAME.md
  - DESIGN_NOTES.md (facility layer)
---

# Sprint 16 Polish & Sprint 21B Component Build-Preview UX

## 1. Purpose

The Sprint 16 facility-simulation foundation has landed: `Facility`, `FacilityComponent`, `FacilityPort`, `InternalConnection`, `apply_facility_components`, `BuildFacilityComponent` / `PreviewBuildFacilityComponent` / `DemolishFacilityComponent` / `PreviewDemolishFacilityComponent`, and tests `test_sprint16a_facility_foundation.py` + `test_sprint16b_facility_editing.py` are all in place. Sprint 21D landed Godot's facility drill-in, port hitboxes, and the wire tool.

The remaining gaps prevent facilities from playing the role the design promises: the seven-kind enum cannot distinguish a smelter from a fabricator, blocked-flow reasons are too coarse to drive the player toward a fix, loader/unloader/platform/power_module/gate_interface rules do not yet feed the freight tick or the world power economy with full fidelity, demolish does not refund cargo trapped in port buffers, and the Godot drill-in panel does not let the player preview-build the new component kinds.

This spec bundles the Sprint 16 polish work with the directly adjacent Sprint 21B slice: backend rules + JSON bridge contract changes + acceptance tests + Godot Local Region UX, all behind backend-owned previews. Compatibility with persisted Sprint-16-foundation save data is mandatory.

## 2. Actors

- **Player (Stage 2)**: drills into a local node from the Local Region scene, opens the facility detail panel, previews adding a smelter / refinery / fabricator / electronics assembler / semiconductor line / extractor head / crusher / sorter / reactor / capacitor bank / warehouse bay, and demolishes any existing component. Reads blocked-flow reasons and loader/platform/power-module diagnostics in the panel.
- **Backend simulation (`gaterail` Python package)**: owns component kind catalog, default ports, default rate/capacity/power, build cost (cash and cargo), blocked-flow reason codes, freight-tick loader/unloader/platform interaction, and aggregation of facility power into the world power economy.
- **JSON bridge (`gaterail.bridge`, stdio mode)**: relays preview/build/demolish commands and surfaces the new diagnostic fields in `render_snapshot()`.
- **Godot Local Region scene (`godot/scenes/local_region.tscn` + `godot/scripts/local_region.gd`)**: extends the existing facility drill-in to handle the new kinds and reason codes. Pure presentation; never invents facility rules.
- **CLI playtester (`gaterail --inspect ...`)**: must still be able to read facility state in plain text.

## 3. Existing Foundation (DO NOT re-implement)

These are already shipped and must be preserved:

- `FacilityComponentKind` enum entries: `PLATFORM`, `LOADER`, `UNLOADER`, `STORAGE_BAY`, `FACTORY_BLOCK`, `POWER_MODULE`, `GATE_INTERFACE`. **Add new kinds; do not remove or rename existing ones.**
- Internal connection flow in `gaterail/facilities.py::apply_facility_components` and `_apply_internal_connections`.
- `Facility.storage_capacity_override`, `loader_rate_override`, `unloader_rate_override`, `power_required` aggregators.
- `_factory_block_open_input_ports` open-port detection and `_missing_inputs` / `_output_port_shortfalls` blocking checks.
- `BuildFacilityComponent`, `PreviewBuildFacilityComponent`, `DemolishFacilityComponent`, `PreviewDemolishFacilityComponent` JSON command wiring.
- Snapshot output in `gaterail.facilities.facility_summary`.
- Save/load round-trip for the seven existing kinds.
- Godot's facility drill-in: `_draw_facility_drill_in`, `_facility_port_hitboxes`, the wire tool's component-box hit testing, and `_facility_port_at`.

## 4. In-Scope Behaviors

### B1. Specialized component kinds

Add the following kinds to `FacilityComponentKind` (string values are stable identifiers; never reuse):

| Kind | String | Role |
|---|---|---|
| `WAREHOUSE_BAY` | `warehouse_bay` | High-capacity buffer (larger default capacity than `storage_bay`) |
| `EXTRACTOR_HEAD` | `extractor_head` | Specialized factory block tied to a deposit; outputs raw resource |
| `CRUSHER` | `crusher` | Sort/concentrate stage between extractor and smelter |
| `SORTER` | `sorter` | Splits mixed ore into typed streams |
| `SMELTER` | `smelter` | Refines ore to bulk metal element |
| `REFINERY` | `refinery` | Refines mixed feedstocks (chemistry/petroleum-style) |
| `CHEMICAL_PROCESSOR` | `chemical_processor` | Industrial chemicals, brines, electrolytes |
| `FABRICATOR` | `fabricator` | Manufactured goods, machine parts |
| `ELECTRONICS_ASSEMBLER` | `electronics_assembler` | Circuit boards, sensors, control systems |
| `SEMICONDUCTOR_LINE` | `semiconductor_line` | Doped silicon, semiconductors |
| `REACTOR` | `reactor` | Power generation from fissile/fusion inputs |
| `CAPACITOR_BANK` | `capacitor_bank` | Stores power for burst gate use |

Each new kind must have:
- A default cash cost in `FACILITY_COMPONENT_BUILD_COST` (suggested floors: warehouse_bay 2200, extractor_head 1800, crusher 1700, sorter 1500, smelter 2800, refinery 3200, chemical_processor 3000, fabricator 2700, electronics_assembler 3500, semiconductor_line 5000, reactor 6000, capacitor_bank 4000).
- A default port template (input/output direction, suggested rate). For example, `SMELTER` defaults to one INPUT port (any cargo) at rate 8 and one OUTPUT port (any cargo) at rate 4; `EXTRACTOR_HEAD` defaults to zero INPUT ports and one OUTPUT port at rate 6.
- A default power requirement (power-module, reactor, capacitor_bank may have NEGATIVE values via a separate `power_provided` field — see B5).
- Optional default cargo build-cost (e.g. `SEMICONDUCTOR_LINE` consumes electronics + machine_parts on build) modeled the same way `NODE_BUILD_CARGO` already works.

`apply_facility_components` must continue to treat any kind whose semantics are "consume inputs → produce outputs" through ports identically to `FACTORY_BLOCK`, except where this spec gives a kind extra behavior (B4, B5, B6).

### B2. Reason-coded blocked-flow reporting

Today `apply_facility_components` records three reason strings: `"open input ports"`, `"missing inputs"`, `"output ports full"`. Replace those plain strings with structured reason codes that survive snapshots and tests:

```python
class FacilityBlockReason(StrEnum):
    OPEN_INPUT_PORTS = "open_input_ports"
    MISSING_INPUTS = "missing_inputs"
    MISSING_NODE_INVENTORY = "missing_node_inventory"   # legacy factory block path
    OUTPUT_PORTS_FULL = "output_ports_full"
    NODE_STORAGE_FULL = "node_storage_full"             # new: factory output blocked at node level
    POWER_SHORTFALL = "power_shortfall"                 # new: insufficient world/local power
    DEMOLISHED = "demolished"                           # transient, only during a tick demolish
```

Each blocked entry must carry `{ "node": ..., "component": ..., "kind": <component kind>, "reason": <FacilityBlockReason>, "detail": {...} }` where `detail` is reason-specific (e.g. cargo map for `MISSING_INPUTS`, single int for `POWER_SHORTFALL`, list of port ids for `OPEN_INPUT_PORTS`).

The existing `state.facility_blocked` aggregate (`{ node_id: [component_ids] }`) must remain backward-compatible. Add a richer `state.facility_block_entries` list keyed on reasons, exposed in render snapshot under `facility_blocked_entries`.

### B3. Loader / unloader / platform freight-tick enforcement

The override functions exist but are not currently consulted everywhere they should be. Lock the following:

- During freight load (`gaterail/freight.py`), a node with at least one `LOADER` component MUST cap per-tick load at `Facility.loader_rate_override()`. With no loader, fall back to the node's `transfer_limit_per_tick`.
- During unload, the same rule applies via `Facility.unloader_rate_override()`.
- A `PLATFORM` component carries an integer `train_capacity` and an optional `concurrent_loading_limit` (default 1). Trains attempting to load/unload at a node beyond the platform's concurrent limit are queued and reported as a new `freight_blocked` entry with reason `platform_capacity`.
- A node with zero `PLATFORM` components but with any `LOADER`/`UNLOADER` continues to load/unload (preserve current behavior). This is a soft constraint until later sprints.
- Emit a tick-level diagnostic `facility_loader_summary` in the operations report that lists per-node effective loader rate and platform queue depth.

### B4. Power-module → world power contribution

Currently `Facility.power_required()` only sums power demand. Add:

- `FacilityComponent.power_provided: int = 0` (new field, default zero).
- `POWER_MODULE` and `REACTOR` defaults populate `power_provided` (e.g. POWER_MODULE 80, REACTOR 250) and `power_required = 0` for those kinds.
- A new `Facility.power_provided()` aggregator.
- A simulation phase `apply_facility_power(state)` that runs before `apply_facility_components` and pushes `Facility.power_provided() - Facility.power_required()` into the owning world's `power_available`/`power_used` accounting. The result must be deterministic and idempotent across save/load.
- A `REACTOR` whose declared `inputs` cannot be satisfied behaves as blocked (`POWER_SHORTFALL` reason on the reactor) and contributes zero `power_provided` for that tick.
- A `CAPACITOR_BANK` exposes a `stored_charge` integer and a `discharge_per_tick` integer; `apply_facility_power` may draw from `stored_charge` to cover transient deficits up to `discharge_per_tick`. Out of scope: charging logic, batched gate burns. Capacitor charging stub returns `0` for now.

### B5. Demolish refund parity

`DemolishFacilityComponent` must:

- Refund 50% of the component's recorded build cost in cash to the world finance.
- Move any cargo currently sitting in the component's `port_inventory` back to the owning node's main inventory, capped by the node's `effective_storage_capacity()` minus current stock; surplus is dropped and logged in the demolish result as `cargo_dropped: { cargo_value: units }`.
- Cancel any internal connections that referenced the demolished component (already handled by stale-connection skip in `_connection_parts`; tests must lock the surface behavior — connections disappear from `Facility.connections` post-demolish, not just become inert).

`PreviewDemolishFacilityComponent` must surface the planned refund amount, the cargo to be returned, and any cargo to be dropped, all without mutating state.

### B6. Snapshot + save round-trip completeness

Every new field introduced by B1-B5 (`power_provided`, `stored_charge`, `discharge_per_tick`, structured block entries, platform `train_capacity` + `concurrent_loading_limit`, demolish refund preview) must:

- Round-trip through `state_to_dict` / `state_from_dict`.
- Appear in `render_snapshot()` so the Godot client and CLI can read them without re-deriving.
- Have a stable JSON key (snake_case, no version suffix in v1).
- Be safe to load from a Sprint-16-foundation save (missing fields default deterministically; load must not raise).

### B7. JSON bridge contract changes

Extend the bridge:

- `PreviewBuildFacilityComponent` accepts the new `kind` strings and returns `{"ok": true/false, "message": ..., "cost": ..., "cargo_cost": {...}, "default_ports": [...], "power_required": ..., "power_provided": ..., "normalized_command": {...}}`. For invalid kinds, return `{"ok": false, "message": "unknown facility component kind: <value>"}` (no bridge-level error).
- `PreviewDemolishFacilityComponent` returns `{"ok": true, "refund": ..., "cargo_returned": {...}, "cargo_dropped": {...}, "connections_removed": [...]}`.
- `render_snapshot()` exposes per-node:
  - `facility.components[i].kind` (string)
  - `facility.components[i].power_provided`
  - `facility.components[i].train_capacity` (only for platform)
  - `facility.components[i].stored_charge`, `discharge_per_tick` (only for capacitor_bank)
  - `facility_block_entries` (list of structured blocks)
  - `loader_summary` (object: `{ effective_loader_rate, effective_unloader_rate, platform_queue_depth }`)
- Existing snapshot keys are preserved.
- Bump `SNAPSHOT_VERSION` from 1 to 2 only if a key is renamed or removed; pure additions stay on version 1.

### B8. Godot Local Region build-preview UX (Sprint 21B adjacent slice)

In `godot/scripts/local_region.gd`:

- The existing facility drill-in panel must render component boxes for every new kind, with a kind-specific glyph or label. Unknown kinds should still draw as a generic factory_block to remain forward-compatible.
- Add an "Add Component" affordance inside the drill-in panel: opens a kind picker (12 buttons), then issues `PreviewBuildFacilityComponent` for the focused kind and renders the returned cost / port template / power_required / power_provided / cargo_cost in the right HUD Build Planner.
- Demolish is invokable from a selected component box (right-click or X key); it issues `PreviewDemolishFacilityComponent`, renders the refund + cargo return + cargo drop + connections-to-remove in the Build Planner, and commits via `DemolishFacilityComponent`.
- Blocked components draw a reason-colored pip in their box header. Hover/select shows the structured reason and detail from `facility_block_entries`. Color map: `OPEN_INPUT_PORTS` amber, `MISSING_INPUTS` red, `OUTPUT_PORTS_FULL` cyan, `NODE_STORAGE_FULL` magenta, `POWER_SHORTFALL` red.
- Platform capacity and loader effective-rate appear in the planet card or a new "Facility Throughput" mini-panel sourced from `loader_summary`.
- Godot must not duplicate any of B1-B5 logic — it reads only what backend snapshots and previews surface.

## 5. Constraints

- **Determinism**: identical input state + identical command sequence must produce identical post-tick state, snapshots, and reports. All new aggregations sort by stable id.
- **Save compatibility**: any save file produced by the current `main` branch (post-Sprint-16-foundation, pre-this-spec) must load without error and run correctly. Missing new fields default to safe values.
- **Backward bridge compatibility**: existing JSON commands must continue to function; new fields are additive. No existing key is renamed or removed in v1.
- **Test discipline**: every backend behavior in §4 must have ≥ 1 pytest test; UX work must have at least a Godot smoke verification documented in `PHASE2_PLAN.md`.
- **Layer purity**: simulation rules live only in `gaterail.facilities` / `gaterail.power` / `gaterail.freight`. Godot code is presentation-only; JSON commands carry no business logic.
- **Determinism of power**: `apply_facility_power` must run before any tick phase that reads `world.power_available`, including `apply_facility_components`, gate evaluation, and freight scheduling.
- **CLI parity**: `gaterail --inspect --report facilities` must show the new component kinds and the new blocked-reason codes in plain text.
- **Cost discipline**: do not introduce a 14th component kind for "advanced gate component assembler" or similar; the 12 listed in B1 are the full v1 set. Adding more is out of scope.

## 6. Acceptance Criteria (concrete, testable)

Each criterion is a pytest-style scenario the implementation must satisfy. The first 80% drive the embrace phase; the last 20% are reserved as the holdout slice.

### AC1 — Specialized kinds are first-class
- Build a smelter via `BuildFacilityComponent(kind="smelter")`. The component appears in the facility, its kind is stored verbatim, the snapshot reports `"kind": "smelter"`, and `facility_component_build_cost(SMELTER)` returns the configured value.

### AC2 — Default port template applies
- Preview-build a `fabricator` with no explicit ports. Response includes `default_ports` with both INPUT and OUTPUT entries. Building with the empty `ports=()` tuple installs those defaults; installing with non-empty `ports=(...)` overrides them.

### AC3 — Reason codes survive snapshots
- Construct a factory_block with no internal connection. Run one tick. `facility_block_entries[0].reason == "open_input_ports"`, `kind == "factory_block"`, and `detail.open_inputs` lists the affected port id.
- Repeat with a missing-inputs scenario; `reason == "missing_inputs"`, `detail` is a cargo map.

### AC4 — Loader rate caps freight load
- Node has a single LOADER with `rate=10`. A train with capacity 50 attempts to load 30 ore. Exactly 10 units load this tick; 20 remain in node inventory; freight report records loader-capped event.

### AC5 — Platform concurrent-loading limit queues trains
- Node has one PLATFORM with `concurrent_loading_limit=1`. Two trains arrive same tick. One loads; the other appears in a `freight_blocked` entry with `reason="platform_capacity"`.

### AC6 — Power module increases world power_available
- World starts with `power_available=100`. Add a POWER_MODULE with `power_provided=80` to a node on that world. Run one tick. `world.power_available == 180` (or equivalent additive form depending on existing accounting), and removing the module restores the prior value next tick.

### AC7 — Reactor blocked when inputs missing
- REACTOR with `inputs={URANIUM: 1}` on a node with no uranium. Tick. Reactor contributes 0 power, blocked entry `reason="power_shortfall"`, world `power_available` unchanged by this reactor.

### AC8 — Demolish refunds cash and returns cargo
- Build a SMELTER (cost 2800), pump 12 units of refined metal into its output port. Demolish.
  - Cash refund: 1400 (50%).
  - 12 units of refined metal added to node inventory (or as much as fits; surplus reported as `cargo_dropped`).
  - All `InternalConnection` referencing the smelter removed from `Facility.connections`.

### AC9 — Preview demolish does not mutate
- Snapshot before `PreviewDemolishFacilityComponent`. Run the preview. Snapshot after. Diff is empty. Preview response carries the same `refund` / `cargo_returned` / `cargo_dropped` / `connections_removed` that a real demolish would produce.

### AC10 — Save round-trip preserves all new fields
- Build one of every new component kind across two facilities. Set platform `train_capacity=2`, capacitor `stored_charge=40`, reactor `inputs={URANIUM: 1}`, power_module `power_provided=80`. Save → load. State is structurally identical (assert via `state_to_dict` round-trip equality on a sorted JSON dump).

### AC11 — Snapshot exposes loader_summary and block entries
- Snapshot of a node with one loader + one platform queue contains `loader_summary` with non-zero `effective_loader_rate` and a `platform_queue_depth` key. `facility_block_entries` is present at the top level.

### AC12 — JSON bridge handles unknown kind gracefully
- Send `PreviewBuildFacilityComponent` with `kind="not_a_real_kind"`. Bridge returns `command_results[0] = {"ok": false, "message": "unknown facility component kind: not_a_real_kind"}`. Bridge does not raise.

### AC13 — Demolish refund is deterministic across two engines
- Same state, same command sequence, run on two independent simulations: identical refund amounts, cargo returns, and dropped-cargo maps.

### AC14 — Godot drill-in handles unknown kinds without crashing
- Render a snapshot containing a component with kind `experimental_thing`. The Local Region scene draws a fallback box, the wire tool can still hit-test ports, and the build planner shows "unknown component kind" rather than erroring.

### AC15 — CLI inspector lists new kinds
- `gaterail --inspect --report facilities` on a scenario with one of each new kind prints kind name, port count, power required, power provided, and current blocked-reason if any, in stable sort order.

### AC16 (holdout candidate) — Capacitor discharge under power deficit
- World has a baseline shortfall of 20 power. A capacitor with `stored_charge=40, discharge_per_tick=10` is present. Tick: world `power_available` reflects +10 from the capacitor; capacitor `stored_charge` decremented by 10; next tick repeats; on tick 5, `stored_charge==0` and the deficit returns.

### AC17 (holdout candidate) — Mixed-kind facility tick order
- A facility containing `EXTRACTOR_HEAD → CRUSHER → SORTER → SMELTER → FABRICATOR` connected end-to-end converts raw ore into machine_parts in a single deterministic chain. Five ticks of run produce a documented exact output count; reordering connection insertion does not change the result.

### AC18 (holdout candidate) — Reactor input recipe gates promotion
- A scenario where a frontier world's tier-promotion requires the reactor to be operational. Without uranium delivery, promotion never occurs (reactor blocked). After uranium is delivered for ≥ N ticks, promotion fires.

### AC19 (holdout candidate) — Demolish during blocked state
- Demolish a smelter that is currently blocked with `OUTPUT_PORTS_FULL`. The trapped output cargo is returned to node inventory or surfaced as `cargo_dropped`; the blocked entry disappears from the next tick's `facility_block_entries`.

### AC20 (holdout candidate) — Godot preview round-trip
- Manual playtest note: in Local Region, open facility drill-in for a depot, click "Add Component → Smelter", verify cost/ports shown, commit, see new component box render, demolish via X, verify refund chip in status strip.

## 7. Out of Scope

- New `FacilityComponentKind` entries beyond the 12 listed in B1.
- Detailed wagon physics, train consists, or rail signal extension (Sprint 21E and later).
- Remote extraction sites, mining missions, orbital yards, collection stations, outposts (Sprint 20).
- 3D facility view (Deferred until full industry/power/space-extraction loops exist).
- Capacitor charging logic, batched gate burns, advanced power scheduling (later Sprint 19/20 follow-ups).
- New world creation, rival operators, tech tree, contract authoring UI.
- Multi-stop route schedules, schedule editing UI.
- Per-tile collision, zoning, terrain costs.
- Resource catalog growth (Sprint 17 follow-ons).

## 8. Open Questions / Risks

- **Reactor input flexibility**: Should a reactor accept either uranium or thorium as one logical fuel, or must each be a separate REACTOR variant? V1 assumes one input cargo; document if changed.
- **Power_provided sign convention**: `power_provided` is a non-negative int; `power_required` is non-negative. World accounting subtracts requireds from provideds. Avoid encoding "consumes 50, produces 30" as a single signed int — use the two fields.
- **Demolish refund 50%**: chosen as a simple deterministic floor. Tunable per-kind in a follow-up but locked at 50% in v1.
- **Capacitor loss**: V1 has zero idle drain; document if tuned.
- **Godot kind picker**: 12 buttons may not fit the right HUD; if not, fall back to a paginated list. Backend has no opinion.
- **Migration concern**: Existing save files predating `power_provided` should default it to zero, which is correct; verify no existing POWER_MODULE save sets a power-required value that would now double-count.

## 9. Glossary

- **Facility**: per-`NetworkNode` internal layout (`gaterail.models.Facility`).
- **FacilityComponent**: one box inside a facility (loader, smelter, etc.).
- **FacilityPort**: typed input/output connector on a component.
- **InternalConnection**: wire between two ports inside one facility.
- **Block entry**: a structured record of why a component could not run this tick.
- **Loader rate override**: aggregate per-tick load rate produced by all loader components on a node, replacing `transfer_limit_per_tick` while loaders exist.
- **Power module**: component that contributes `power_provided` to its world.
- **Capacitor bank**: component with `stored_charge` that can cover transient deficits up to `discharge_per_tick`.
- **Drill-in panel**: the Godot Local Region facility view introduced in Sprint 21D.
- **Build Planner**: the Godot right-HUD panel that mirrors backend preview results.

---

## Spec Self-Adversarial Notes

A second-provider completeness pass was simulated locally. Surfaced concerns folded into B/AC sections:

1. **Are loader/unloader effects on freight already enforced?** Behavior B3 / AC4 explicitly demand it; assume current code may or may not honor it and treat as new work.
2. **Does power_provided risk double-counting with `gaterail.power`?** B4 + open question §8 flag the migration.
3. **Does demolish leave dangling connections?** Existing code skips stale connections at runtime but may not remove them from `Facility.connections`. AC8 locks removal.
4. **Are reason codes machine-readable today?** They are plain strings; B2 + AC3 promote them to a typed enum.
5. **Is Godot tolerant of unknown kinds?** AC14 forces a fallback render path before adding new kinds.
6. **Does the snapshot expose facility power for the gate economy to consume?** B6 + B7 require it.
7. **Does the spec say what NOT to build?** Section 7 enumerates out-of-scope deliberately to keep factory mode focused.
