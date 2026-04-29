"""Plain-text reporting helpers for GateRail."""

from __future__ import annotations

from gaterail.economy import specialization_profiles_for_state
from gaterail.gate import preview_gate_power
from gaterail.models import Contract, ContractKind, GameState, LinkMode
from gaterail.resource_chains import resource_branch_pressure
from gaterail.resources import resource_definition
from gaterail.traffic import build_signal_report
from gaterail.transport import shortest_route


def _contract_summary_target(contract: Contract) -> str:
    """One-liner target descriptor for inspection output."""

    if contract.kind == ContractKind.CARGO_DELIVERY:
        cargo = contract.cargo_type.value if contract.cargo_type is not None else "?"
        return f"{cargo} x{contract.target_units} to {contract.destination_node_id}"
    if contract.kind == ContractKind.FRONTIER_SUPPORT:
        return f"support streak {contract.target_units} on {contract.target_world_id}"
    if contract.kind == ContractKind.GATE_RECOVERY:
        return f"recover {contract.target_link_id} for {contract.target_units} ticks"
    return f"target {contract.target_units}"


ReportSections = set[str] | frozenset[str] | None


def _section_enabled(sections: ReportSections, section: str) -> bool:
    """Return whether a report section should be rendered."""

    return sections is None or section in sections


def _format_node_rollup(label: str, rollup: object) -> str:
    """Format a node-to-cargo report map."""

    if not isinstance(rollup, dict) or not rollup:
        return f"{label}: none"
    parts: list[str] = []
    for node_id, cargo_map in rollup.items():
        if not isinstance(cargo_map, dict):
            continue
        cargo_parts = [f"{cargo} {units}" for cargo, units in cargo_map.items()]
        parts.append(f"{node_id} ({', '.join(cargo_parts)})")
    return f"{label}: {'; '.join(parts) if parts else 'none'}"


def _ticks_label(ticks: object) -> str:
    """Format tick counts with a stable singular/plural label."""

    count = int(ticks)
    unit = "tick" if count == 1 else "ticks"
    return f"{count} {unit}"


def _format_resource_profile(mapping: object) -> str:
    """Format an import/export profile map."""

    if not isinstance(mapping, dict) or not mapping:
        return "none"
    return ", ".join(f"{cargo} {units}" for cargo, units in mapping.items())


def _format_resource_map(mapping: object) -> str:
    """Format a resource-id map for terminal reports."""

    if not isinstance(mapping, dict) or not mapping:
        return "none"
    return ", ".join(f"{resource} {units}" for resource, units in mapping.items())


def _format_cargo_map(mapping: object) -> str:
    """Format a cargo map for terminal reports."""

    if not isinstance(mapping, dict) or not mapping:
        return "none"
    return ", ".join(
        f"{getattr(cargo, 'value', cargo)} {units}"
        for cargo, units in sorted(
            mapping.items(),
            key=lambda item: str(getattr(item[0], "value", item[0])),
        )
    )


def _format_string_list(value: object) -> str:
    """Format a JSON-style list of ids for terminal reports."""

    if not isinstance(value, list) or not value:
        return "-"
    return ", ".join(str(item) for item in value)


def _format_node_resource_rollup(label: str, rollup: object) -> str:
    """Format a node-to-resource report map."""

    if not isinstance(rollup, dict) or not rollup:
        return f"{label}: none"
    parts: list[str] = []
    for node_id, resource_map in rollup.items():
        if not isinstance(resource_map, dict):
            continue
        resource_parts = [f"{resource} {units}" for resource, units in resource_map.items()]
        parts.append(f"{node_id} ({', '.join(resource_parts)})")
    return f"{label}: {'; '.join(parts) if parts else 'none'}"


def _format_resource_distribution(rollup: object) -> str:
    """Format node-to-node resource movement."""

    if not isinstance(rollup, dict) or not rollup:
        return "Resource Moves: none"
    parts: list[str] = []
    for source_id, targets in rollup.items():
        if not isinstance(targets, dict):
            continue
        for target_id, resource_map in targets.items():
            if not isinstance(resource_map, dict):
                continue
            parts.append(f"{source_id}->{target_id} ({_format_resource_map(resource_map)})")
    return "Resource Moves: " + ("; ".join(parts) if parts else "none")


def _format_resource_branch_pressure(pressure: object) -> str:
    """Format resource branch-pressure warnings."""

    if not isinstance(pressure, list) or not pressure:
        return "Resource Branches: nominal"
    parts: list[str] = []
    for entry in pressure[:4]:
        if not isinstance(entry, dict):
            continue
        parts.append(
            f"{entry.get('severity', 'watch')} {entry.get('node', '?')} "
            f"degree {entry.get('degree', 0)} {entry.get('recipe_kind') or '-'}"
        )
    return "Resource Branches: " + ("; ".join(parts) if parts else "nominal")


def _format_resource_chains_rollup(chains: object) -> str:
    """Format resource extraction, processing, and blockers."""

    if not isinstance(chains, dict):
        return "Resources: none"
    segments: list[str] = []
    extracted = chains.get("extracted")
    if isinstance(extracted, dict) and extracted:
        segments.append(_format_node_resource_rollup("extracted", extracted))
    distributed = chains.get("distributed")
    if isinstance(distributed, dict) and distributed:
        segments.append(_format_resource_distribution(distributed))
    recipes = chains.get("recipes")
    if isinstance(recipes, dict):
        produced = recipes.get("produced")
        if isinstance(produced, dict) and produced:
            segments.append(_format_node_resource_rollup("processed", produced))
        blocked = recipes.get("blocked")
        if isinstance(blocked, list) and blocked:
            parts: list[str] = []
            for event in blocked[:4]:
                if not isinstance(event, dict):
                    continue
                missing = event.get("missing")
                missing_text = _format_resource_map(missing)
                parts.append(
                    f"{event.get('node', '?')} {event.get('recipe', '?')}: "
                    f"{event.get('reason', 'blocked')} ({missing_text})"
                )
            if parts:
                segments.append("blocked " + "; ".join(parts))
    pressure = chains.get("branch_pressure")
    if isinstance(pressure, list) and pressure:
        segments.append(_format_resource_branch_pressure(pressure))
    return "Resources: " + (" | ".join(segments) if segments else "none")


def _format_resource_deposit_summary(state: GameState) -> str:
    """Format a compact resource-deposit summary."""

    if not state.resource_deposits:
        return "none"
    parts: list[str] = []
    for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id):
        world = state.worlds[deposit.world_id]
        definition = resource_definition(deposit.resource_id)
        parts.append(
            f"{world.name} {deposit.name} {definition.name} "
            f"grade {deposit.grade:.2f} yield {deposit.yield_per_tick}/tick"
        )
    return "; ".join(parts)


def _block_reason_value(reason: object) -> str:
    """Return a stable blocked-reason value for plain-text reports."""

    return reason.value if hasattr(reason, "value") else str(reason)


def _facility_block_reasons_by_component(state: GameState) -> dict[tuple[str, str], list[str]]:
    """Group facility block reasons by node/component pair."""

    grouped: dict[tuple[str, str], list[str]] = {}
    for entry in state.facility_block_entries:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node", ""))
        component_id = str(entry.get("component", ""))
        if not node_id or not component_id:
            continue
        grouped.setdefault((node_id, component_id), []).append(
            _block_reason_value(entry.get("reason"))
        )
    return grouped


def format_state_summary(state: GameState) -> str:
    """Format a compact scenario summary."""

    rail_links = state.links_by_mode(LinkMode.RAIL)
    gate_links = state.links_by_mode(LinkMode.GATE)
    world_lines = [
        f"{world.name} tier {int(world.tier)} pop {world.population} power margin {world.power_margin}"
        for world in state.worlds.values()
    ]
    lines = [
        f"Scenario: {len(state.worlds)} worlds, {len(state.nodes)} nodes, "
        f"{len(rail_links)} rail links, {len(gate_links)} gate links, "
        f"{len(state.trains)} trains, {len(state.orders)} orders",
        "Worlds: " + "; ".join(world_lines),
    ]
    if state.resource_deposits:
        lines.append("Deposits: " + _format_resource_deposit_summary(state))
    if state.trains:
        train_lines = [
            f"{train.name} at {train.node_id} capacity {train.capacity}"
            for train in state.trains.values()
        ]
        lines.append("Trains: " + "; ".join(train_lines))
    gate_statuses = preview_gate_power(state)
    if gate_statuses:
        gate_lines = []
        for link_id, status in gate_statuses.items():
            state_label = "powered" if status.powered else f"underpowered short {status.power_shortfall}"
            gate_lines.append(
                f"{link_id} {state_label} from {status.source_world_name} "
                f"requires {status.power_required}"
            )
        lines.append("Gates: " + "; ".join(gate_lines))
    if state.orders:
        order_lines: list[str] = []
        for order in state.orders.values():
            route = shortest_route(state, order.origin, order.destination)
            travel = "unrouted" if route is None else _ticks_label(route.travel_ticks)
            order_lines.append(
                f"{order.id} {order.cargo_type.value} {order.origin}->{order.destination} "
                f"{order.requested_units} units via {travel}"
            )
        lines.append("Orders: " + "; ".join(order_lines))
    if state.schedules:
        schedule_lines = [
            f"{schedule.id} {schedule.cargo_type.value} {schedule.origin}->{schedule.destination} "
            f"{schedule.units_per_departure} units every {schedule.interval_ticks} ticks"
            for schedule in state.schedules.values()
        ]
        lines.append("Schedules: " + "; ".join(schedule_lines))
    if state.disruptions:
        disruption_lines = [
            f"{disruption.id} {disruption.link_id} ticks {disruption.start_tick}-{disruption.end_tick} "
            f"capacity x{disruption.capacity_multiplier} {disruption.reason}"
            for disruption in state.disruptions.values()
        ]
        lines.append("Disruptions: " + "; ".join(disruption_lines))
    if state.power_plants:
        plant_lines = []
        for plant in sorted(state.power_plants.values(), key=lambda item: item.id):
            node = state.nodes[plant.node_id]
            plant_lines.append(
                f"{plant.id} {plant.kind.value} at {node.id} "
                f"output {plant.power_output} inputs {_format_resource_map(plant.inputs)}"
            )
        lines.append("Power Plants: " + "; ".join(plant_lines))
    if state.track_signals:
        signal_lines = [
            f"{signal.id} {signal.kind.value} {signal.link_id}"
            for signal in sorted(state.track_signals.values(), key=lambda item: item.id)
        ]
        lines.append("Signals: " + "; ".join(signal_lines))
    if state.contracts:
        contract_lines: list[str] = []
        for contract in sorted(state.contracts.values(), key=lambda item: item.id):
            target = _contract_summary_target(contract)
            contract_lines.append(
                f"{contract.id} {contract.kind.value} {target} by tick {contract.due_tick} "
                f"(reward {round(contract.reward_cash, 2)}c/+{contract.reward_reputation}rep, "
                f"penalty {round(contract.penalty_cash, 2)}c/-{contract.penalty_reputation}rep)"
            )
        lines.append("Contracts: " + "; ".join(contract_lines))
    profiles = getattr(state, "economic_identity_enabled", False)
    if profiles:
        economy_lines = [
            f"{world.name} {world.specialization}"
            for world in state.worlds.values()
            if world.specialization is not None
        ]
        lines.append("Economy: " + "; ".join(economy_lines))
        profile_lines = []
        for world_id, profile in specialization_profiles_for_state(state).items():
            world = state.worlds[world_id]
            imports = _format_resource_profile(profile.get("imports"))
            exports = _format_resource_profile(profile.get("exports"))
            profile_lines.append(f"{world.name} imports {imports} exports {exports}")
        if profile_lines:
            lines.append("Economy Profiles: " + "; ".join(profile_lines))
    return "\n".join(lines)


def format_scenario_inspection(state: GameState, sections: ReportSections = None) -> str:
    """Format a scenario inspection report without advancing time."""

    lines = ["Scenario Inspection", format_state_summary(state)]

    if _section_enabled(sections, "traffic") or _section_enabled(sections, "gates"):
        link_rows = [
            (
                link.id,
                link.mode.value,
                f"{link.origin}->{link.destination}",
                link.travel_ticks,
                link.capacity_per_tick,
                link.power_required,
                "yes" if link.active else "no",
            )
            for link in sorted(state.links.values(), key=lambda item: item.id)
        ]
        lines.extend(
            [
                "",
                "Network Links",
                _format_table(("Link", "Mode", "Route", "Ticks", "Capacity", "Power", "Active"), link_rows),
            ]
        )

    if _section_enabled(sections, "schedules"):
        schedule_rows = [
            (
                schedule.id,
                schedule.train_id,
                f"{schedule.origin}->{schedule.destination}",
                schedule.cargo_type.value,
                schedule.units_per_departure,
                schedule.interval_ticks,
                schedule.next_departure_tick,
                "yes" if schedule.active else "no",
            )
            for schedule in sorted(state.schedules.values(), key=lambda item: item.id)
        ]
        lines.extend(
            [
                "",
                "Schedule Plan",
                _format_table(
                    ("Schedule", "Train", "Route", "Cargo", "Units", "Every", "Next", "Active"),
                    schedule_rows,
                ),
            ]
        )

    if _section_enabled(sections, "stockpiles"):
        stockpile_rows: list[tuple[object, ...]] = []
        for node in sorted(state.nodes.values(), key=lambda item: item.id):
            if not node.inventory:
                stockpile_rows.append((node.id, node.name, "empty", 0))
                continue
            for cargo_type, units in sorted(node.inventory.items(), key=lambda item: item[0].value):
                stockpile_rows.append((node.id, node.name, cargo_type.value, units))
        lines.extend(
            [
                "",
                "Initial Stockpiles",
                _format_table(("Node", "Name", "Cargo", "Units"), stockpile_rows),
            ]
        )

    if _section_enabled(sections, "resources"):
        deposit_rows: list[tuple[object, ...]] = []
        for deposit in sorted(state.resource_deposits.values(), key=lambda item: item.id):
            world = state.worlds[deposit.world_id]
            definition = resource_definition(deposit.resource_id)
            deposit_rows.append(
                (
                    world.name,
                    deposit.name,
                    definition.id,
                    definition.category.value,
                    f"{deposit.grade:.2f}",
                    deposit.yield_per_tick,
                    "yes" if deposit.discovered else "no",
                )
            )
        lines.extend(
            [
                "",
                "Resource Deposits",
                _format_table(
                    ("World", "Deposit", "Resource", "Category", "Grade", "Yield", "Known"),
                    deposit_rows,
                ),
            ]
        )
        chain_rows: list[tuple[object, ...]] = []
        for node in sorted(state.nodes.values(), key=lambda item: item.id):
            if (
                not node.resource_inventory
                and not node.resource_production
                and node.resource_recipe is None
                and node.resource_deposit_id is None
            ):
                continue
            recipe = "-"
            if node.resource_recipe is not None:
                recipe = (
                    f"{node.resource_recipe.id} [{node.resource_recipe.kind.value}]: "
                    f"{_format_resource_map(node.resource_recipe.inputs)} -> "
                    f"{_format_resource_map(node.resource_recipe.outputs)}"
                )
            deposit = "-"
            if node.resource_deposit_id is not None:
                deposit_model = state.resource_deposits.get(node.resource_deposit_id)
                deposit = node.resource_deposit_id if deposit_model is None else deposit_model.name
            chain_rows.append(
                (
                    node.id,
                    node.name,
                    deposit,
                    _format_resource_map(node.resource_inventory),
                    recipe,
                )
            )
        lines.extend(
            [
                "",
                "Resource Chain Nodes",
                _format_table(("Node", "Name", "Deposit", "Inventory", "Recipe"), chain_rows),
            ]
        )
        pressure_rows = [
            (
                entry["node"],
                entry["severity"],
                entry["degree"],
                entry["recipe_kind"] or "-",
                ", ".join(entry["resource_links"]),
            )
            for entry in resource_branch_pressure(state)
        ]
        lines.extend(
            [
                "",
                "Resource Branch Pressure",
                _format_table(("Node", "Severity", "Degree", "Recipe Kind", "Links"), pressure_rows),
            ]
        )

    if _section_enabled(sections, "facilities"):
        block_reasons = _facility_block_reasons_by_component(state)
        facility_rows: list[tuple[object, ...]] = []
        for node in sorted(state.nodes.values(), key=lambda item: item.id):
            if node.facility is None:
                continue
            for component in sorted(node.facility.components.values(), key=lambda item: item.id):
                reasons = block_reasons.get((node.id, component.id), [])
                facility_rows.append(
                    (
                        node.id,
                        component.id,
                        component.kind.value,
                        len(component.ports),
                        component.power_required,
                        component.power_provided,
                        component.train_capacity,
                        component.concurrent_loading_limit,
                        component.stored_charge,
                        _format_cargo_map(component.inputs),
                        _format_cargo_map(component.outputs),
                        ", ".join(reasons) if reasons else "-",
                    )
                )
        lines.extend(
            [
                "",
                "Facility Components",
                _format_table(
                    (
                        "Node",
                        "Component",
                        "Kind",
                        "Ports",
                        "power_required",
                        "power_provided",
                        "train_capacity",
                        "load_limit",
                        "stored_charge",
                        "Inputs",
                        "Outputs",
                        "Blocked",
                    ),
                    facility_rows,
                ),
            ]
        )

    if _section_enabled(sections, "signals"):
        signal_rows = [
            (
                signal.id,
                signal.kind.value,
                signal.link_id,
                signal.node_id or "-",
                "yes" if signal.active else "no",
            )
            for signal in sorted(state.track_signals.values(), key=lambda item: item.id)
        ]
        signal_report = build_signal_report(state)
        block_rows = [
            (
                block.get("block", link_id),
                _format_string_list(block.get("signal_ids")),
                _format_string_list(block.get("occupiers")),
                block.get("reserved_by") or "-",
            )
            for link_id, block in signal_report["blocks"].items()
            if isinstance(block, dict)
        ]
        lines.extend(
            [
                "",
                "Track Signals",
                _format_table(("Signal", "Kind", "Link", "Node", "Active"), signal_rows),
                "",
                "Rail Blocks",
                _format_table(("Block", "Signals", "Occupiers", "Reserved By"), block_rows),
            ]
        )

    if _section_enabled(sections, "power"):
        power_rows = [
            (
                world.id,
                world.name,
                world.power_available,
                world.power_generated_this_tick,
                world.power_used,
                world.gate_power_used,
                world.power_margin,
            )
            for world in sorted(state.worlds.values(), key=lambda item: item.id)
        ]
        plant_rows = [
            (
                plant.id,
                plant.kind.value,
                plant.node_id,
                state.nodes[plant.node_id].world_id,
                _format_resource_map(plant.inputs),
                plant.power_output,
                "yes" if plant.active else "no",
            )
            for plant in sorted(state.power_plants.values(), key=lambda item: item.id)
        ]
        lines.extend(
            [
                "",
                "World Power",
                _format_table(
                    ("World", "Name", "Static", "Generated", "Used", "Gate Used", "Margin"),
                    power_rows,
                ),
                "",
                "Power Plants",
                _format_table(("Plant", "Kind", "Node", "World", "Inputs", "Output", "Active"), plant_rows),
            ]
        )

    if _section_enabled(sections, "finance"):
        finance = state.finance.snapshot()
        lines.extend(
            [
                "",
                "Starting Finance",
                _format_table(
                    ("Cash", "Revenue Total", "Costs Total", "Net Total"),
                    [
                        (
                            finance["cash"],
                            finance["revenue_total"],
                            finance["costs_total"],
                            finance["net_total"],
                        )
                    ],
                ),
            ]
        )

    if _section_enabled(sections, "contracts") and state.contracts:
        contract_rows: list[tuple[object, ...]] = []
        for contract in sorted(state.contracts.values(), key=lambda item: item.id):
            contract_rows.append(
                (
                    contract.id,
                    contract.kind.value,
                    contract.title,
                    _contract_summary_target(contract),
                    contract.target_units,
                    contract.due_tick,
                    round(contract.reward_cash, 2),
                    round(contract.penalty_cash, 2),
                    contract.reward_reputation,
                    contract.penalty_reputation,
                )
            )
        lines.extend(
            [
                "",
                "Active Contracts",
                _format_table(
                    (
                        "Contract",
                        "Kind",
                        "Title",
                        "Target",
                        "Goal",
                        "Due",
                        "Reward",
                        "Penalty",
                        "Rep+",
                        "Rep-",
                    ),
                    contract_rows,
                ),
            ]
        )

    return "\n".join(lines)


def format_tick_report(report: dict[str, object], sections: ReportSections = None) -> str:
    """Format one fixed-tick report for terminal output."""

    network = report.get("network", {})
    if not isinstance(network, dict):
        network = {}
    lines = [
        f"Tick {int(report['tick']):04d} | "
        f"rail {network.get('rail_links', 0)} | "
        f"gates {network.get('powered_gate_links', 0)}/{network.get('gate_links', 0)} powered | "
        f"trains {network.get('trains', 0)} | "
        f"gate power {network.get('gate_power_required', 0)}",
    ]
    if _section_enabled(sections, "production"):
        lines.append(_format_node_rollup("Produced", report.get("produced")))
        lines.append(_format_node_rollup("Consumed", report.get("consumed")))
    if _section_enabled(sections, "economy"):
        lines.append(_format_economy_rollup(report.get("economy")))
    if _section_enabled(sections, "power"):
        lines.append(_format_power_generation_rollup(report.get("power_generation")))
    if _section_enabled(sections, "gates"):
        lines.append(_format_gate_rollup(report.get("gates")))
    if _section_enabled(sections, "traffic"):
        lines.append(_format_traffic_rollup(report.get("traffic")))
    if _section_enabled(sections, "signals"):
        lines.append(_format_signal_rollup(report.get("signals")))
    if _section_enabled(sections, "freight"):
        lines.append(_format_freight_rollup(report.get("freight")))
    if _section_enabled(sections, "contracts"):
        lines.append(_format_contracts_rollup(report.get("contracts")))
    if _section_enabled(sections, "progression"):
        lines.append(_format_progression_rollup(report.get("progression")))
    if _section_enabled(sections, "resources"):
        lines.append(_format_resource_chains_rollup(report.get("resource_chains")))
    if _section_enabled(sections, "shortages"):
        lines.append(_format_node_rollup("Shortages", report.get("shortages")))
    if _section_enabled(sections, "finance"):
        lines.append(_format_finance_rollup(report.get("finance")))
    return "\n".join(lines)


def _format_contracts_rollup(contracts: object) -> str:
    """Format contract progress, resolutions, and reputation."""

    if not isinstance(contracts, dict):
        return "Contracts: none"

    segments: list[str] = []
    active = contracts.get("active")
    if isinstance(active, list) and active:
        parts: list[str] = []
        for entry in active[:4]:
            if not isinstance(entry, dict):
                continue
            parts.append(
                f"{entry.get('id', '?')} {entry.get('delivered', 0)}/{entry.get('target', 0)} "
                f"{entry.get('cargo', '?')} to {entry.get('destination', '?')} "
                f"in {_ticks_label(entry.get('ticks_remaining', 0))}"
            )
        if parts:
            segments.append("active " + "; ".join(parts))

    fulfilled = contracts.get("fulfilled_this_tick")
    if isinstance(fulfilled, list) and fulfilled:
        parts = [
            f"{event.get('contract', '?')} +{event.get('reward_cash', 0)}c "
            f"+{event.get('reward_reputation', 0)}rep"
            for event in fulfilled
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("fulfilled " + "; ".join(parts))

    failed = contracts.get("failed_this_tick")
    if isinstance(failed, list) and failed:
        parts = [
            f"{event.get('contract', '?')} -{event.get('penalty_cash', 0)}c "
            f"-{event.get('penalty_reputation', 0)}rep "
            f"({event.get('delivered_units', 0)}/{event.get('target_units', 0)})"
            for event in failed
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("failed " + "; ".join(parts))

    reputation = contracts.get("reputation")
    if isinstance(reputation, int):
        segments.append(f"reputation {reputation}")

    return "Contracts: " + (" | ".join(segments) if segments else "none")


def _format_gate_rollup(gates: object) -> str:
    """Format powered and underpowered gate links."""

    if not isinstance(gates, dict) or not gates:
        return "Gates: none"
    parts: list[str] = []
    for link_id, status in gates.items():
        if not isinstance(status, dict):
            continue
        source = status.get("source_world_name", status.get("source_world", "unknown"))
        required = status.get("power_required", 0)
        support = ""
        if status.get("support_id") is not None:
            bonus = status.get("resource_power_bonus", 0)
            support_node = status.get("support_node_id", "?")
            missing = status.get("support_missing")
            if isinstance(missing, dict) and missing:
                support = f" support waiting {support_node} missing {_format_resource_map(missing)}"
            elif bonus:
                support = f" supported by {support_node} bonus {bonus}"
        if status.get("powered"):
            parts.append(
                f"{link_id} powered by {source} draw {required} "
                f"slots {status.get('slots_used', 0)}/{status.get('slot_capacity', 0)}{support}"
            )
        else:
            parts.append(
                f"{link_id} underpowered by {source} short {status.get('power_shortfall', 0)}{support}"
            )
    return "Gates: " + ("; ".join(parts) if parts else "none")


def _format_power_generation_rollup(power_generation: object) -> str:
    """Format generated power and plant blockers."""

    if not isinstance(power_generation, dict):
        return "Power: none"
    segments: list[str] = []
    generated = power_generation.get("generated")
    if isinstance(generated, dict) and generated:
        parts = [f"{world} +{power}" for world, power in generated.items()]
        segments.append("generated " + ", ".join(parts))

    consumed = power_generation.get("consumed")
    if isinstance(consumed, dict) and consumed:
        parts = [
            f"{plant} ({_format_resource_map(inputs)})"
            for plant, inputs in consumed.items()
            if isinstance(inputs, dict)
        ]
        if parts:
            segments.append("consumed " + "; ".join(parts))

    blocked = power_generation.get("blocked")
    if isinstance(blocked, list) and blocked:
        parts = []
        for event in blocked[:4]:
            if not isinstance(event, dict):
                continue
            parts.append(
                f"{event.get('plant', '?')}: {event.get('reason', 'blocked')} "
                f"({_format_resource_map(event.get('missing'))})"
            )
        if parts:
            segments.append("blocked " + "; ".join(parts))

    return "Power: " + (" | ".join(segments) if segments else "none")


def _format_traffic_rollup(traffic: object) -> str:
    """Format congestion and disruption telemetry."""

    if not isinstance(traffic, dict):
        return "Traffic: none"
    alerts = traffic.get("alerts", [])
    if not isinstance(alerts, list) or not alerts:
        return "Traffic: nominal"

    parts: list[str] = []
    for alert in alerts[:4]:
        if not isinstance(alert, dict):
            continue
        link = alert.get("link", "unknown")
        severity = alert.get("severity", "alert")
        used = alert.get("used", 0)
        capacity = alert.get("capacity", 0)
        reason = alert.get("reason", "capacity pressure")
        parts.append(f"{severity} {link} {used}/{capacity} {reason}")
    return "Traffic: " + ("; ".join(parts) if parts else "nominal")


def _format_signal_rollup(signals: object) -> str:
    """Format signal-block occupancy and blockers."""

    if not isinstance(signals, dict):
        return "Signals: none"
    blocked = signals.get("blocked")
    if isinstance(blocked, list) and blocked:
        parts = [
            f"{event.get('train_id', 'unknown')} on {event.get('link', 'unknown')}: "
            f"{event.get('reason', 'blocked')}"
            for event in blocked
            if isinstance(event, dict)
        ]
        if parts:
            return "Signals: blocked " + "; ".join(parts)

    blocks = signals.get("blocks")
    if not isinstance(blocks, dict) or not blocks:
        return "Signals: none"
    occupied_parts: list[str] = []
    clear_count = 0
    for link_id, block in blocks.items():
        if not isinstance(block, dict):
            continue
        occupiers = block.get("occupiers")
        if isinstance(occupiers, list) and occupiers:
            occupied_parts.append(
                f"{link_id} occupied by {', '.join(str(item) for item in occupiers)}"
            )
        else:
            clear_count += 1
    if occupied_parts:
        return "Signals: " + "; ".join(occupied_parts)
    return f"Signals: {clear_count} clear block{'s' if clear_count != 1 else ''}"


def _format_economy_rollup(economy: object) -> str:
    """Format specialization-driven production."""

    if not isinstance(economy, dict):
        return "Economy: none"
    produced = economy.get("produced", {})
    blocked = economy.get("blocked", [])
    segments: list[str] = []

    if isinstance(produced, dict) and produced:
        produced_parts: list[str] = []
        for node_id, cargo_map in produced.items():
            if not isinstance(cargo_map, dict):
                continue
            cargo_parts = [f"{cargo} {units}" for cargo, units in cargo_map.items()]
            produced_parts.append(f"{node_id} ({', '.join(cargo_parts)})")
        if produced_parts:
            segments.append("produced " + "; ".join(produced_parts))

    if isinstance(blocked, list) and blocked:
        blocked_parts: list[str] = []
        for event in blocked[:3]:
            if not isinstance(event, dict):
                continue
            reason = event.get("reason", "blocked")
            recipe = event.get("recipe", "unknown")
            missing = event.get("missing")
            if isinstance(missing, dict) and missing:
                missing_text = ", ".join(f"{cargo} {units}" for cargo, units in missing.items())
                blocked_parts.append(f"{recipe}: {reason} ({missing_text})")
            else:
                blocked_parts.append(f"{recipe}: {reason}")
        if blocked_parts:
            segments.append("blocked " + "; ".join(blocked_parts))

    return "Economy: " + (" | ".join(segments) if segments else "none")


def _format_freight_rollup(freight: object) -> str:
    """Format freight dispatch, transit, delivery, and blocking events."""

    if not isinstance(freight, dict):
        return "Freight: none"

    segments: list[str] = []
    dispatches = freight.get("dispatches")
    if isinstance(dispatches, list) and dispatches:
        parts = [
            f"{event['train']} loaded {event['units']} {event['cargo']} "
            f"{event['origin']}->{event['destination']} ({_ticks_label(event['travel_ticks'])})"
            for event in dispatches
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("dispatch " + "; ".join(parts))

    in_transit = freight.get("in_transit")
    if isinstance(in_transit, list) and in_transit:
        parts = [
            f"{event['train']}->{event['destination']} {_ticks_label(event['remaining_ticks'])}"
            for event in in_transit
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("moving " + "; ".join(parts))

    deliveries = freight.get("deliveries")
    if isinstance(deliveries, list) and deliveries:
        parts = [
            f"{event['train']} delivered {event['units']} {event['cargo']} to {event['node']}"
            for event in deliveries
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("delivered " + "; ".join(parts))

    blocked = freight.get("blocked")
    if isinstance(blocked, list) and blocked:
        parts = [
            f"{event.get('train', 'unknown')}: {event.get('reason', 'blocked')}"
            for event in blocked
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("blocked " + "; ".join(parts))

    queued = freight.get("queued")
    if isinstance(queued, list) and queued:
        parts = [
            f"{event.get('train', 'unknown')} on {event.get('link', 'unknown')}: {event.get('reason', 'queued')}"
            for event in queued
            if isinstance(event, dict)
        ]
        if parts:
            segments.append("queued " + "; ".join(parts))

    return "Freight: " + (" | ".join(segments) if segments else "none")


def _format_progression_rollup(progression: object) -> str:
    """Format world development state."""

    if not isinstance(progression, dict) or not progression:
        return "Progression: none"

    parts: list[str] = []
    for world_id, report in progression.items():
        if not isinstance(report, dict):
            continue
        name = report.get("name", world_id)
        trend = report.get("trend", "stalled")
        tier_name = report.get("tier_name", "unknown")
        stability = report.get("stability", 0)
        support_streak = report.get("support_streak", 0)
        required = report.get("supported_ticks_required", 0)
        promoted_to = report.get("promoted_to")
        bottlenecks = report.get("bottlenecks")

        if promoted_to:
            parts.append(f"{name} promoted to {promoted_to} stability {stability}")
            continue

        label = (
            f"{name} {trend} tier {tier_name} stability {stability} "
            f"support {support_streak}/{required}"
        )
        if isinstance(bottlenecks, list) and bottlenecks:
            label += " bottlenecks " + ", ".join(str(item) for item in bottlenecks[:3])
        parts.append(label)

    return "Progression: " + ("; ".join(parts) if parts else "none")


def _format_finance_rollup(finance: object) -> str:
    """Format one tick of operating finance."""

    if not isinstance(finance, dict):
        return "Finance: none"
    return (
        f"Finance: revenue {finance.get('revenue', 0)} | "
        f"costs {finance.get('costs', 0)} | "
        f"net {finance.get('net', 0)} | "
        f"cash {finance.get('cash', 0)}"
    )


def _format_table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> str:
    """Format a compact fixed-width text table."""

    if not rows:
        rows = [("none",) + ("",) * (len(headers) - 1)]
    widths = [
        max(len(str(header)), *(len(str(row[index])) for row in rows))
        for index, header in enumerate(headers)
    ]
    header_line = " | ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers))
    rule = "-+-".join("-" * width for width in widths)
    body = [
        " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, rule, *body])


def format_monthly_report(report: dict[str, object], sections: ReportSections = None) -> str:
    """Format a month-end Stage 1 operations ledger."""

    finance = report.get("finance", {})
    if not isinstance(finance, dict):
        finance = {}

    cargo_moved = report.get("cargo_moved", {})
    cargo_rows = [
        (cargo, units)
        for cargo, units in (cargo_moved.items() if isinstance(cargo_moved, dict) else [])
    ]

    shortages = report.get("shortages", {})
    shortage_rows = [
        (cargo, units)
        for cargo, units in (shortages.items() if isinstance(shortages, dict) else [])
    ]

    gate_use = report.get("gate_use", {})
    gate_rows = []
    if isinstance(gate_use, dict):
        for gate_id, data in gate_use.items():
            if isinstance(data, dict):
                gate_rows.append(
                    (
                        gate_id,
                        data.get("slots_used", 0),
                        data.get("powered_ticks", 0),
                        data.get("underpowered_ticks", 0),
                    )
                )

    specialized_output = report.get("specialized_output", {})
    specialized_rows = [
        (cargo, units)
        for cargo, units in (specialized_output.items() if isinstance(specialized_output, dict) else [])
    ]

    traffic_pressure = report.get("traffic_pressure", {})
    traffic_rows = []
    if isinstance(traffic_pressure, dict):
        for link_id, data in traffic_pressure.items():
            if isinstance(data, dict):
                traffic_rows.append(
                    (
                        link_id,
                        data.get("peak_used", 0),
                        data.get("peak_pressure", 0),
                        data.get("full_ticks", 0),
                        data.get("disrupted_ticks", 0),
                    )
                )

    stockpiles = report.get("stockpiles", {})
    stockpile_rows = []
    if isinstance(stockpiles, dict):
        for node_id, cargo_map in stockpiles.items():
            if not isinstance(cargo_map, dict) or not cargo_map:
                stockpile_rows.append((node_id, "empty", 0))
                continue
            for cargo, units in cargo_map.items():
                stockpile_rows.append((node_id, cargo, units))

    schedules = report.get("schedules", {})
    schedule_rows = []
    if isinstance(schedules, dict):
        for schedule_id, data in schedules.items():
            if not isinstance(data, dict):
                continue
            schedule_rows.append(
                (
                    schedule_id,
                    data.get("train", "?"),
                    f"{data.get('origin', '?')}->{data.get('destination', '?')}",
                    data.get("cargo", "?"),
                    data.get("dispatched", 0),
                    data.get("completed", 0),
                    data.get("delivered_units", 0),
                    data.get("next_departure_tick", "?"),
                )
            )

    lines = [
        f"Month {int(report.get('month', 0)):02d} Operations Ledger "
        f"(ticks {report.get('start_tick', '?')}-{report.get('end_tick', '?')})",
    ]
    if _section_enabled(sections, "finance"):
        lines.extend(
            [
                "",
                "Finance",
                _format_table(
                    ("Revenue", "Costs", "Net", "Ending Cash"),
                    [
                        (
                            finance.get("revenue", 0),
                            finance.get("costs", 0),
                            finance.get("net", 0),
                            finance.get("ending_cash", 0),
                        )
                    ],
                ),
            ]
        )
    if _section_enabled(sections, "cargo"):
        lines.extend(["", "Cargo Moved", _format_table(("Cargo", "Units"), cargo_rows)])
    if _section_enabled(sections, "shortages"):
        lines.extend(["", "Shortages", _format_table(("Cargo", "Units"), shortage_rows)])
    if _section_enabled(sections, "gates"):
        lines.extend(["", "Gate Use", _format_table(("Gate", "Slots", "Powered", "Underpowered"), gate_rows)])
    if _section_enabled(sections, "economy"):
        lines.extend(["", "Specialized Output", _format_table(("Cargo", "Units"), specialized_rows)])
    if _section_enabled(sections, "traffic"):
        lines.extend(
            [
                "",
                "Traffic Pressure",
                _format_table(("Link", "Peak Used", "Peak Pressure", "Full Ticks", "Disrupted Ticks"), traffic_rows),
            ]
        )
    if _section_enabled(sections, "schedules"):
        lines.extend(
            [
                "",
                "Schedule Status",
                _format_table(
                    ("Schedule", "Train", "Route", "Cargo", "Dispatched", "Completed", "Delivered", "Next"),
                    schedule_rows,
                ),
            ]
        )
    if _section_enabled(sections, "stockpiles"):
        lines.extend(["", "Settlement Stockpiles", _format_table(("Node", "Cargo", "Units"), stockpile_rows)])
    if _section_enabled(sections, "contracts"):
        contracts = report.get("contracts", {})
        totals = report.get("contract_totals", {})
        reputation = report.get("reputation", 0)
        contract_rows = []
        if isinstance(contracts, dict):
            for contract_id, data in contracts.items():
                if not isinstance(data, dict):
                    continue
                contract_rows.append(
                    (
                        contract_id,
                        data.get("status", "?"),
                        data.get("cargo", "?"),
                        data.get("destination", "?"),
                        f"{data.get('delivered', 0)}/{data.get('target', 0)}",
                        data.get("due_tick", "?"),
                        data.get("resolved_tick", "-"),
                    )
                )
        totals_label = "-"
        if isinstance(totals, dict):
            totals_label = (
                f"fulfilled {totals.get('fulfilled', 0)} | "
                f"failed {totals.get('failed', 0)} | "
                f"active {totals.get('active', 0)} | "
                f"reputation {reputation}"
            )
        lines.extend(
            [
                "",
                f"Contracts ({totals_label})",
                _format_table(
                    ("Contract", "Status", "Cargo", "Destination", "Progress", "Due", "Resolved"),
                    contract_rows,
                ),
            ]
        )
    return "\n".join(lines)
