# GateRail

GateRail is a command-line prototype for testing one question: **can a single logistics loop keep an isolated settlement supplied, solvent, and stable over repeated cycles?**

The prototype proves the core interaction model works end to end:
- A settlement reports demand each cycle.
- Cargo and route decisions are applied.
- Budget and throughput are updated.
- A text report summarizes outcomes and highlights bottlenecks.

## What the prototype proves

This prototype is intentionally narrow. It demonstrates that a small, deterministic simulation can:
- run fully from the terminal,
- produce repeatable cycle-level metrics,
- expose tradeoffs between delivery reliability and operating cost,
- provide a base for future rule modules without changing the core loop.

It is **not** a content-complete simulation yet; it is a systems prototype validating structure and signal quality.

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

## Run commands

Run the default scenario:

```bash
python -m gaterail.main
```

Run with explicit cycle count (example):

```bash
python -m gaterail.main --cycles 12
```

Run the test suite:

```bash
pytest
```

## Sample output

Example of the text-style output shape (values shown as illustrative):

```text
Cycle 01 | Demand 120 | Delivered 116 | Utilization 0.97
Revenue 2320 | Cost 1980 | Net 340 | Reserve 5340
Alerts: minor shortfall in cold storage lane

Cycle 02 | Demand 122 | Delivered 122 | Utilization 1.00
Revenue 2440 | Cost 2050 | Net 390 | Reserve 5730
Alerts: none
```

Actual values depend on scenario parameters and command-line options.

## Core loop explanation

GateRail runs a repeated **sense -> plan -> move -> settle -> report** loop:

1. **Sense**: read demand, stock, and route state for the current cycle.
2. **Plan**: allocate cargo and schedule movement under available capacity.
3. **Move**: apply transit outcomes and delivery completion.
4. **Settle**: update finances, reserves, and persistent state.
5. **Report**: emit a concise cycle summary to standard output.

This loop is small by design so future systems can plug into one phase at a time.

## Future ideas

- Add disruption events (weather, maintenance, route delays) as opt-in rule packs.
- Add policy presets for conservative, balanced, and growth-oriented planning.
- Add richer scenario authoring from structured data files.
- Add end-of-run comparative reports for parameter sweeps.
- Add stability scoring to detect fragile but profitable plans.
