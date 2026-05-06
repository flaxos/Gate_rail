# Tutorial Vertical Slice

The canonical tutorial scenario is `tutorial_six_worlds` (`tutorial_start` alias).
It starts with six stocked ring worlds and one unsurveyed destination world,
Sable Reach.

Run the scenario inspection:

```bash
PYTHONPATH=src python3 -m gaterail.main --scenario tutorial_six_worlds --inspect --report schedules,stockpiles,gates,space
```

Run the JSON-over-stdio bridge for Godot:

```bash
PYTHONPATH=src python3 -m gaterail.main --scenario tutorial_six_worlds --stdio
```

Vertical-slice path:

1. Activate ore, metal, and Helix parts schedules.
2. Feed Atlas gateworks with parts and electronics.
3. Deliver manufactured aperture control components to `atlas_outbound_gate`.
4. Survey `site_sable_reach`.
5. Build `gate_atlas_sable` from `atlas_outbound_gate` to `sable_gate_anchor`.
6. Activate `tutorial_starter_to_sable`.
7. Complete the tutorial when `sable_starter_cargo` is fulfilled.

The Python backend owns the tutorial state, blockers, commands, recipes,
construction project, Railgate link, and freight movement. Godot reads snapshot
state and sends backend command payloads.
