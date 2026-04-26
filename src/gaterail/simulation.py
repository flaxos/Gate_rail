"""Main simulation loop and day execution order."""

from __future__ import annotations

from dataclasses import dataclass, field

from gaterail.cargo import CargoType
from gaterail.contracts import advance_contracts
from gaterail.economy import (
    apply_buffer_distribution,
    apply_node_demand,
    apply_node_production,
    apply_node_recipes,
    apply_specialized_production,
    update_transfer_saturation_streaks,
)
from gaterail.facilities import apply_facility_components
from gaterail.freight import advance_freight
from gaterail.gate import evaluate_gate_power
from gaterail.models import GameState, GatePowerStatus, LinkMode
from gaterail.operations import build_monthly_report
from gaterail.progression import apply_world_progression
from gaterail.scenarios import DEFAULT_SCENARIO, load_scenario
from gaterail.traffic import build_traffic_report, reset_traffic_usage


def _plain_cargo_map(mapping: dict[CargoType, int]) -> dict[str, int]:
    """Convert cargo-keyed maps to stable report dictionaries."""

    return {cargo_type.value: units for cargo_type, units in sorted(mapping.items(), key=lambda item: item[0].value)}


def _plain_node_cargo_map(mapping: dict[str, dict[CargoType, int]]) -> dict[str, dict[str, int]]:
    """Convert node cargo rollups to stable report dictionaries."""

    return {
        node_id: _plain_cargo_map(cargo_map)
        for node_id, cargo_map in sorted(mapping.items())
    }


def _plain_buffer_distribution(
    mapping: dict[str, dict[str, dict[CargoType, int]]],
) -> dict[str, dict[str, dict[str, int]]]:
    """Convert buffer-distribution rollups to stable report dictionaries."""

    return {
        source_id: {
            target_id: _plain_cargo_map(cargo_map)
            for target_id, cargo_map in sorted(per_source.items())
        }
        for source_id, per_source in sorted(mapping.items())
    }


def _plain_gate_status_map(mapping: dict[str, GatePowerStatus]) -> dict[str, dict[str, object]]:
    """Convert gate power statuses to stable report dictionaries."""

    return {
        link_id: {
            "source_world": status.source_world_id,
            "source_world_name": status.source_world_name,
            "power_required": status.power_required,
            "power_available": status.power_available,
            "power_shortfall": status.power_shortfall,
            "powered": status.powered,
            "active": status.active,
            "slot_capacity": status.slot_capacity,
            "slots_used": status.slots_used,
            "slots_remaining": status.slots_remaining,
        }
        for link_id, status in sorted(mapping.items())
    }


@dataclass(slots=True)
class TickSimulation:
    """Fixed-tick simulation foundation for the multi-world prototype."""

    state: GameState
    status: str = "running"
    reports: list[dict[str, object]] = field(default_factory=list)
    monthly_reports: list[dict[str, object]] = field(default_factory=list)

    @classmethod
    def from_scenario(cls, name: str = DEFAULT_SCENARIO) -> TickSimulation:
        """Create a tick simulation from a built-in scenario."""

        return cls(state=load_scenario(name))

    def step_tick(self) -> dict[str, object]:
        """Advance the simulation by one deterministic tick."""

        if self.status != "running":
            return {"tick": self.state.tick, "status": self.status, "message": "simulation not running"}

        phase_order: list[str] = []
        self.state.finance.reset_tick()
        self.state.transfer_used_this_tick = {}
        self.state.tick += 1
        phase_order.append("advance_time")

        produced = apply_node_production(self.state)
        phase_order.append("node_production")

        buffer_distribution = apply_buffer_distribution(self.state)
        phase_order.append("buffer_distribution")

        recipes_result = apply_node_recipes(self.state)
        phase_order.append("node_recipes")

        facilities_result = apply_facility_components(self.state)
        phase_order.append("facility_components")

        demand_result = apply_node_demand(self.state)
        phase_order.append("node_demand")

        economy_result = apply_specialized_production(self.state)
        phase_order.append("specialized_production")

        gate_result = evaluate_gate_power(self.state)
        gate_power_cost = sum(status.power_required for status in gate_result.values() if status.powered) * 0.5
        self.state.finance.record_cost(gate_power_cost)
        phase_order.append("gate_power")

        reset_traffic_usage(self.state)
        phase_order.append("traffic_reset")

        freight_result = advance_freight(self.state)
        phase_order.append("freight_movement")

        update_transfer_saturation_streaks(self.state)
        phase_order.append("transfer_saturation")

        # Persist shortages on state for snapshot rendering
        self.state.shortages = demand_result.shortages

        traffic_result = build_traffic_report(self.state)
        phase_order.append("traffic_report")

        progression_result = apply_world_progression(self.state)
        phase_order.append("world_progression")

        contracts_result = advance_contracts(self.state, freight_result, progression_result)
        phase_order.append("contract_resolution")

        rail_links = self.state.links_by_mode(LinkMode.RAIL)
        gate_links = self.state.links_by_mode(LinkMode.GATE)
        phase_order.append("network_snapshot")

        report: dict[str, object] = {
            "tick": self.state.tick,
            "status": self.status,
            "phase_order": phase_order,
            "produced": _plain_node_cargo_map(produced),
            "consumed": _plain_node_cargo_map(demand_result.consumed),
            "shortages": _plain_node_cargo_map(demand_result.shortages),
            "buffer_distribution": _plain_buffer_distribution(buffer_distribution),
            "recipes": recipes_result,
            "facilities": facilities_result,
            "economy": economy_result,
            "gates": _plain_gate_status_map(gate_result),
            "traffic": traffic_result,
            "freight": freight_result,
            "contracts": contracts_result,
            "progression": progression_result,
            "finance": self.state.finance.snapshot(),
            "reputation": self.state.reputation,
            "network": {
                "worlds": len(self.state.worlds),
                "nodes": len(self.state.nodes),
                "rail_links": len(rail_links),
                "gate_links": len(gate_links),
                "powered_gate_links": sum(1 for status in gate_result.values() if status.powered),
                "unpowered_gate_links": sum(1 for status in gate_result.values() if not status.powered),
                "trains": len(self.state.trains),
                "orders": len(self.state.orders),
                "gate_power_required": sum(
                    status.power_required for status in gate_result.values() if status.powered
                ),
            },
        }
        self.reports.append(report)
        if self.state.tick % self.state.month_length == 0:
            self.monthly_reports.append(
                build_monthly_report(
                    self.state,
                    self.reports[-self.state.month_length:],
                    month_length=self.state.month_length,
                )
            )
        return report

    def run_ticks(self, ticks: int) -> list[dict[str, object]]:
        """Run a bounded number of fixed ticks."""

        reports: list[dict[str, object]] = []
        for _ in range(max(0, ticks)):
            if self.status != "running":
                break
            reports.append(self.step_tick())
        return reports
