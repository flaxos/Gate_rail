"""Stage 1 operations ledger and monthly report aggregation."""

from __future__ import annotations

from gaterail.cargo import CargoType
from gaterail.models import ContractStatus, GameState, NodeKind


def _add_cargo(total: dict[str, int], cargo: str, units: int) -> None:
    """Accumulate cargo totals by string key."""

    if units <= 0:
        return
    total[cargo] = total.get(cargo, 0) + units


def _format_inventory(inventory: dict[CargoType, int]) -> dict[str, int]:
    """Convert cargo-keyed inventory to stable string-keyed inventory."""

    return {
        cargo_type.value: units
        for cargo_type, units in sorted(inventory.items(), key=lambda item: item[0].value)
        if units > 0
    }


def build_monthly_report(
    state: GameState,
    reports: list[dict[str, object]],
    *,
    month_length: int,
) -> dict[str, object]:
    """Aggregate fixed-tick reports into a month-end operations ledger."""

    cargo_moved: dict[str, int] = {}
    shortages: dict[str, int] = {}
    gate_use: dict[str, dict[str, int]] = {}
    specialized_output: dict[str, int] = {}
    traffic_pressure: dict[str, dict[str, float | int]] = {}
    revenue = 0.0
    costs = 0.0
    contract_events_fulfilled: list[dict[str, object]] = []
    contract_events_failed: list[dict[str, object]] = []

    for report in reports:
        freight = report.get("freight", {})
        if isinstance(freight, dict):
            deliveries = freight.get("deliveries", [])
            if isinstance(deliveries, list):
                for event in deliveries:
                    if not isinstance(event, dict):
                        continue
                    _add_cargo(cargo_moved, str(event.get("cargo", "unknown")), int(event.get("units", 0)))

        shortage_report = report.get("shortages", {})
        if isinstance(shortage_report, dict):
            for cargo_map in shortage_report.values():
                if not isinstance(cargo_map, dict):
                    continue
                for cargo, units in cargo_map.items():
                    _add_cargo(shortages, str(cargo), int(units))

        gates = report.get("gates", {})
        if isinstance(gates, dict):
            for link_id, status in gates.items():
                if not isinstance(status, dict):
                    continue
                gate = gate_use.setdefault(
                    str(link_id),
                    {
                        "slots_used": 0,
                        "powered_ticks": 0,
                        "underpowered_ticks": 0,
                    },
                )
                gate["slots_used"] += int(status.get("slots_used", 0))
                if status.get("powered"):
                    gate["powered_ticks"] += 1
                else:
                    gate["underpowered_ticks"] += 1

        economy = report.get("economy", {})
        if isinstance(economy, dict):
            produced = economy.get("produced", {})
            if isinstance(produced, dict):
                for cargo_map in produced.values():
                    if not isinstance(cargo_map, dict):
                        continue
                    for cargo, units in cargo_map.items():
                        _add_cargo(specialized_output, str(cargo), int(units))

        traffic = report.get("traffic", {})
        if isinstance(traffic, dict):
            links = traffic.get("links", {})
            if isinstance(links, dict):
                for link_id, status in links.items():
                    if not isinstance(status, dict):
                        continue
                    entry = traffic_pressure.setdefault(
                        str(link_id),
                        {
                            "peak_used": 0,
                            "peak_pressure": 0.0,
                            "full_ticks": 0,
                            "disrupted_ticks": 0,
                        },
                    )
                    used = int(status.get("used", 0))
                    pressure = float(status.get("pressure", 0.0))
                    entry["peak_used"] = max(int(entry["peak_used"]), used)
                    entry["peak_pressure"] = max(float(entry["peak_pressure"]), pressure)
                    if status.get("congested"):
                        entry["full_ticks"] = int(entry["full_ticks"]) + 1
                    if status.get("disrupted"):
                        entry["disrupted_ticks"] = int(entry["disrupted_ticks"]) + 1

        finance = report.get("finance", {})
        if isinstance(finance, dict):
            revenue += float(finance.get("revenue", 0.0))
            costs += float(finance.get("costs", 0.0))

        contracts_report = report.get("contracts", {})
        if isinstance(contracts_report, dict):
            fulfilled = contracts_report.get("fulfilled_this_tick", [])
            if isinstance(fulfilled, list):
                for event in fulfilled:
                    if isinstance(event, dict):
                        contract_events_fulfilled.append(event)
            failed = contracts_report.get("failed_this_tick", [])
            if isinstance(failed, list):
                for event in failed:
                    if isinstance(event, dict):
                        contract_events_failed.append(event)

    stockpiles = {
        node_id: _format_inventory(node.inventory)
        for node_id, node in sorted(state.nodes.items())
        if node.kind == NodeKind.SETTLEMENT
    }
    schedules = {
        schedule_id: {
            "train": schedule.train_id,
            "origin": schedule.origin,
            "destination": schedule.destination,
            "cargo": schedule.cargo_type.value,
            "units_per_departure": schedule.units_per_departure,
            "interval_ticks": schedule.interval_ticks,
            "next_departure_tick": schedule.next_departure_tick,
            "dispatched": schedule.trips_dispatched,
            "completed": schedule.trips_completed,
            "delivered_units": schedule.delivered_units,
            "active": schedule.active,
        }
        for schedule_id, schedule in sorted(state.schedules.items())
    }
    month = 0 if not reports else (int(reports[-1]["tick"]) // month_length)
    contracts = {}
    for contract in sorted(state.contracts.values(), key=lambda item: item.id):
        if contract.kind.value == "cargo_delivery":
            cargo_label = contract.cargo_type.value if contract.cargo_type is not None else "?"
            destination_label = contract.destination_node_id or "?"
            progress_value = contract.delivered_units
        elif contract.kind.value == "frontier_support":
            cargo_label = "support"
            destination_label = f"world:{contract.target_world_id}"
            progress_value = contract.progress
        else:
            cargo_label = "powered"
            destination_label = f"link:{contract.target_link_id}"
            progress_value = contract.progress
        contracts[contract.id] = {
            "title": contract.title,
            "kind": contract.kind.value,
            "status": contract.status.value,
            "cargo": cargo_label,
            "destination": destination_label,
            "delivered": progress_value,
            "target": contract.target_units,
            "due_tick": contract.due_tick,
            "resolved_tick": contract.resolved_tick,
            "reward_cash": round(contract.reward_cash, 2),
            "penalty_cash": round(contract.penalty_cash, 2),
            "reward_reputation": contract.reward_reputation,
            "penalty_reputation": contract.penalty_reputation,
        }
    contract_totals = {
        "fulfilled": sum(
            1 for contract in state.contracts.values() if contract.status == ContractStatus.FULFILLED
        ),
        "failed": sum(
            1 for contract in state.contracts.values() if contract.status == ContractStatus.FAILED
        ),
        "active": sum(
            1 for contract in state.contracts.values() if contract.status == ContractStatus.ACTIVE
        ),
    }
    return {
        "month": month,
        "start_tick": reports[0]["tick"] if reports else state.tick,
        "end_tick": reports[-1]["tick"] if reports else state.tick,
        "cargo_moved": dict(sorted(cargo_moved.items())),
        "shortages": dict(sorted(shortages.items())),
        "gate_use": dict(sorted(gate_use.items())),
        "specialized_output": dict(sorted(specialized_output.items())),
        "traffic_pressure": {
            link_id: {
                "peak_used": int(data["peak_used"]),
                "peak_pressure": round(float(data["peak_pressure"]), 2),
                "full_ticks": int(data["full_ticks"]),
                "disrupted_ticks": int(data["disrupted_ticks"]),
            }
            for link_id, data in sorted(traffic_pressure.items())
            if int(data["peak_used"]) > 0 or int(data["full_ticks"]) > 0 or int(data["disrupted_ticks"]) > 0
        },
        "stockpiles": stockpiles,
        "schedules": schedules,
        "finance": {
            "revenue": round(revenue, 2),
            "costs": round(costs, 2),
            "net": round(revenue - costs, 2),
            "ending_cash": round(state.finance.cash, 2),
        },
        "contracts": contracts,
        "contract_totals": contract_totals,
        "contract_events": {
            "fulfilled": contract_events_fulfilled,
            "failed": contract_events_failed,
        },
        "reputation": state.reputation,
    }
