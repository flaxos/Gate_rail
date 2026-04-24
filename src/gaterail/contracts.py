"""Contract progress, fulfillment, and expiry for the Stage 1 objectives layer."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.models import Contract, ContractKind, ContractStatus, GameState
from gaterail.traffic import effective_link_capacity


ContractReport = dict[str, object]


def _delivery_match(contract: Contract, event: dict[str, object]) -> int:
    """Return units in a delivery event that apply to ``contract``."""

    if contract.status != ContractStatus.ACTIVE:
        return 0
    if event.get("node") != contract.destination_node_id:
        return 0
    try:
        cargo = CargoType(str(event.get("cargo")))
    except ValueError:
        return 0
    if cargo != contract.cargo_type:
        return 0
    return max(0, int(event.get("units", 0)))


def _fulfill(state: GameState, contract: Contract) -> dict[str, object]:
    """Mark a contract fulfilled and apply its reward."""

    contract.status = ContractStatus.FULFILLED
    contract.resolved_tick = state.tick
    state.finance.record_revenue(contract.reward_cash)
    state.reputation += contract.reward_reputation
    return {
        "contract": contract.id,
        "kind": contract.kind.value,
        "title": contract.title,
        "tick": state.tick,
        "reward_cash": round(contract.reward_cash, 2),
        "reward_reputation": contract.reward_reputation,
    }


def _fail(state: GameState, contract: Contract) -> dict[str, object]:
    """Mark a contract failed and apply its penalty."""

    contract.status = ContractStatus.FAILED
    contract.resolved_tick = state.tick
    state.finance.record_cost(contract.penalty_cash)
    state.reputation -= contract.penalty_reputation
    return {
        "contract": contract.id,
        "kind": contract.kind.value,
        "title": contract.title,
        "tick": state.tick,
        "penalty_cash": round(contract.penalty_cash, 2),
        "penalty_reputation": contract.penalty_reputation,
        "delivered_units": contract.delivered_units,
        "progress": contract.progress,
        "target_units": contract.target_units,
    }


def _resolve_cargo_delivery(
    state: GameState, contract: Contract, delivery_events: list[dict[str, object]]
) -> bool:
    """Apply delivery events to a cargo-delivery contract. Return True if fulfilled."""

    for event in delivery_events:
        applied = _delivery_match(contract, event)
        if applied <= 0:
            continue
        needed = contract.remaining_units
        take = min(applied, needed)
        if take <= 0:
            break
        contract.delivered_units += take
        if contract.delivered_units >= contract.target_units:
            break
    return contract.delivered_units >= contract.target_units


def _resolve_frontier_support(
    state: GameState, contract: Contract, progression_result: dict[str, object]
) -> bool:
    """Count supported-or-promoted ticks for a world. Return True if target reached."""

    world_id = contract.target_world_id or ""
    report = progression_result.get(world_id) if isinstance(progression_result, dict) else None
    if isinstance(report, dict):
        trend = report.get("trend")
        if trend in ("improving", "promoted"):
            contract.progress += 1
    return contract.progress >= contract.target_units


def _resolve_gate_recovery(state: GameState, contract: Contract) -> bool:
    """Count consecutive operational ticks on a gate link. Return True if target reached."""

    link_id = contract.target_link_id or ""
    status = state.gate_statuses.get(link_id)
    link = state.links.get(link_id)
    operational = False
    if status is not None and status.powered and link is not None:
        capacity, _ = effective_link_capacity(state, link)
        operational = capacity > 0
    if operational:
        contract.progress += 1
    else:
        contract.progress = 0
    return contract.progress >= contract.target_units


def _contract_snapshot(state: GameState, contract: Contract) -> dict[str, object]:
    """Return report-safe progress data for a contract."""

    ticks_remaining = max(0, contract.due_tick - state.tick)
    if contract.kind == ContractKind.CARGO_DELIVERY:
        progress_value = contract.delivered_units
        destination_label = contract.destination_node_id or "?"
        cargo_label = contract.cargo_type.value if contract.cargo_type is not None else "?"
    elif contract.kind == ContractKind.FRONTIER_SUPPORT:
        progress_value = contract.progress
        destination_label = f"world:{contract.target_world_id}"
        cargo_label = "support"
    else:
        progress_value = contract.progress
        destination_label = f"link:{contract.target_link_id}"
        cargo_label = "powered"
    return {
        "id": contract.id,
        "title": contract.title,
        "kind": contract.kind.value,
        "destination": destination_label,
        "cargo": cargo_label,
        "delivered": progress_value,
        "target": contract.target_units,
        "remaining": max(0, contract.target_units - progress_value),
        "due_tick": contract.due_tick,
        "ticks_remaining": ticks_remaining,
        "status": contract.status.value,
        "reward_cash": round(contract.reward_cash, 2),
        "penalty_cash": round(contract.penalty_cash, 2),
        "reward_reputation": contract.reward_reputation,
        "penalty_reputation": contract.penalty_reputation,
        "resolved_tick": contract.resolved_tick,
        "client": contract.client,
        "target_world_id": contract.target_world_id,
        "target_link_id": contract.target_link_id,
    }


def advance_contracts(
    state: GameState,
    freight_events: dict[str, object],
    progression_result: dict[str, object] | None = None,
) -> ContractReport:
    """Apply tick progress to active contracts, resolve fulfillments and missed deadlines."""

    fulfilled: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    deliveries = freight_events.get("deliveries", []) if isinstance(freight_events, dict) else []
    delivery_events = [event for event in deliveries if isinstance(event, dict)]
    progression = progression_result if isinstance(progression_result, dict) else {}

    for contract in sorted(state.contracts.values(), key=lambda item: item.id):
        if contract.status != ContractStatus.ACTIVE:
            continue
        if contract.kind == ContractKind.CARGO_DELIVERY:
            completed = _resolve_cargo_delivery(state, contract, delivery_events)
        elif contract.kind == ContractKind.FRONTIER_SUPPORT:
            completed = _resolve_frontier_support(state, contract, progression)
        elif contract.kind == ContractKind.GATE_RECOVERY:
            completed = _resolve_gate_recovery(state, contract)
        else:
            completed = False
        if completed:
            fulfilled.append(_fulfill(state, contract))
            continue
        if state.tick >= contract.due_tick:
            failed.append(_fail(state, contract))

    active_contracts = [
        _contract_snapshot(state, contract)
        for contract in sorted(state.contracts.values(), key=lambda item: item.id)
        if contract.status == ContractStatus.ACTIVE
    ]
    resolved_counts = {
        "fulfilled": sum(
            1 for contract in state.contracts.values() if contract.status == ContractStatus.FULFILLED
        ),
        "failed": sum(
            1 for contract in state.contracts.values() if contract.status == ContractStatus.FAILED
        ),
        "active": len(active_contracts),
    }
    return {
        "active": active_contracts,
        "fulfilled_this_tick": fulfilled,
        "failed_this_tick": failed,
        "totals": resolved_counts,
        "reputation": state.reputation,
    }
