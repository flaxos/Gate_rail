# Design Notes

## Concept

GateRail models a closed-loop freight service that keeps a remote settlement supplied through repeated transport cycles.
The design emphasizes clear state transitions, deterministic behavior, and actionable telemetry over visual fidelity.

The current concept target is a **CLI-first systems prototype**:
- fast to run,
- easy to inspect,
- straightforward to extend with new rules.

## Five design pillars

1. **Deterministic execution**  
   Given the same inputs and seed settings, runs should produce the same outputs.

2. **Cycle clarity**  
   Every cycle should expose demand, delivery, capacity, and finance signals in plain text.

3. **Composable rules**  
   New mechanics should be introduced as focused modules instead of entangling core flow.

4. **Constrained complexity**  
   Prefer simple rules with meaningful interactions over large opaque formulas.

5. **Operational relevance**  
   Metrics and alerts should help answer practical planning questions, not just produce numbers.

## Future systems list

- **Disruption system**: stochastic delays, downtime, and recovery windows.
- **Maintenance system**: wear, service intervals, and availability penalties.
- **Contract system**: time-boxed delivery obligations with bonus/penalty logic.
- **Policy system**: configurable planning heuristics and budget priorities.
- **Market system**: variable buy/sell rates and demand elasticity.
- **Storage system**: perishability tiers, overflow handling, and spoilage losses.
- **Progression system**: phased infrastructure upgrades and capability unlocks.
- **Analytics system**: multi-run comparison, trend summaries, and stability scoring.
