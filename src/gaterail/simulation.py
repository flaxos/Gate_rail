"""Main simulation loop and day execution order."""

from __future__ import annotations

from dataclasses import dataclass, field

from gaterail.cargo import CargoType
from gaterail.colony import Colony
from gaterail.finance import CorporateFinance
from gaterail.gate import WormholeGate
from gaterail.schedule import DailySchedule, ScheduleResult
from gaterail.train import Train
from gaterail.world import World


@dataclass(slots=True)
class Simulation:
    """Coordinates all game systems in strict daily sequence."""

    world: World = field(default_factory=World.default)
    gate: WormholeGate = field(default_factory=WormholeGate)
    trains: list[Train] = field(default_factory=lambda: [Train(name="Atlas"), Train(name="Nova", capacity=16)])
    colony: Colony = field(default_factory=Colony)
    finance: CorporateFinance = field(default_factory=CorporateFinance)
    day: int = 0
    max_days: int = 365
    status: str = "running"
    reports: list[dict[str, object]] = field(default_factory=list)

    def build_default_schedule(self) -> DailySchedule:
        """Build default schedule using required cargo priorities."""

        return DailySchedule.generate_default(self.world)

    def run_day(self, schedule: DailySchedule | None = None) -> dict[str, object]:
        """Execute one simulation day in strict order and return a report."""

        if self.status != "running":
            return {"day": self.day, "status": self.status, "message": "simulation not running"}

        self.day += 1
        self.world.reset_day()
        phase_order: list[str] = []
        delivered_to_frontier: dict[CargoType, int] = {}

        # 1) reset gate slots
        self.gate.reset_daily_slots()
        for train in self.trains:
            train.reset_day()
        self.finance.reset_daily_totals()
        phase_order.append("reset_gate_slots")

        # 2) world production
        produced = self.world.produce()
        phase_order.append("world_production")

        # 3) build schedule
        working_schedule = schedule if schedule is not None else self.build_default_schedule()
        phase_order.append("build_schedule")

        # 4) process by priority
        ordered = working_schedule.ordered()
        phase_order.append("process_by_priority")

        # 5) move cargo
        result = ScheduleResult()
        jumps = 0
        for movement in ordered:
            if movement.units <= 0:
                continue
            if not self.gate.allocate_slots(1):
                result.skipped.append(
                    f"No gate slot available for {movement.cargo_type} {movement.origin}->{movement.destination}"
                )
                continue

            planned_units = self.world.available(movement.origin, movement.cargo_type)
            planned_units = min(planned_units, movement.units)
            if planned_units <= 0:
                result.skipped.append(
                    f"No cargo available for {movement.cargo_type} at {movement.origin}"
                )
                continue

            remaining = planned_units
            for train in self.trains:
                if remaining <= 0:
                    break
                trip = train.move(
                    movement.cargo_type,
                    movement.origin,
                    movement.destination,
                    requested_units=remaining,
                )
                if trip is None:
                    continue
                loaded = self.world.remove_cargo(movement.origin, movement.cargo_type, trip.units)
                self.world.add_cargo(movement.destination, movement.cargo_type, loaded)
                remaining -= loaded
                result.executed.append(
                    {
                        "train": trip.train_name,
                        "cargo": trip.cargo_type,
                        "origin": trip.origin,
                        "destination": trip.destination,
                        "units": loaded,
                        "revenue": trip.revenue,
                        "cost": trip.cost,
                    }
                )
                result.moved_units[movement.cargo_type] = result.moved_units.get(movement.cargo_type, 0) + loaded
                self.finance.record_revenue(trip.revenue)
                self.finance.record_cost(trip.cost)
                if movement.destination == "Frontier":
                    delivered_to_frontier[movement.cargo_type] = (
                        delivered_to_frontier.get(movement.cargo_type, 0) + loaded
                    )
            jumps += 1
        phase_order.append("move_cargo")

        # 6) train revenue/costs
        train_financials = {
            "revenue": self.finance.revenue_today,
            "costs": self.finance.costs_today,
            "net": self.finance.revenue_today - self.finance.costs_today,
        }
        phase_order.append("train_revenue_costs")

        # 7) gate costs
        gate_cost = self.gate.daily_operating_cost()
        self.finance.record_cost(gate_cost)
        phase_order.append("gate_costs")

        # 8) wear
        self.gate.apply_wear(jumps)
        phase_order.append("wear")

        # 9) colony updates
        colony_update = self.colony.update(delivered_to_frontier)
        phase_order.append("colony_updates")

        # 10) debt payment
        interest = self.finance.accrue_daily_interest()
        interest_cost = interest
        if interest_cost > 0:
            self.finance.record_cost(interest_cost)
        debt_payment = self.finance.pay_debt()
        phase_order.append("debt_payment")

        # 11) reporting data
        finance_snapshot = self.finance.close_day()
        report = {
            "day": self.day,
            "phase_order": phase_order,
            "produced": produced,
            "schedule_result": result,
            "train_financials": train_financials,
            "gate_cost": gate_cost,
            "colony": colony_update,
            "interest": interest,
            "debt_payment": debt_payment,
            "finance": finance_snapshot,
            "status": "running",
        }
        self.reports.append(report)
        phase_order.append("reporting_data")

        # 12) failure/success checks
        if self.finance.insolvent:
            self.status = "failed"
            report["status"] = self.status
            report["reason"] = "insolvent"
        elif not self.gate.operational:
            self.status = "failed"
            report["status"] = self.status
            report["reason"] = "gate_failed"
        elif self.colony.failed:
            self.status = "failed"
            report["status"] = self.status
            report["reason"] = "colony_failed"
        elif self.day >= self.max_days and self.finance.cash > 0 and self.colony.population > 0:
            self.status = "success"
            report["status"] = self.status
            report["reason"] = "survived_duration"
        phase_order.append("failure_success_checks")

        return report

    def run(self, days: int | None = None) -> list[dict[str, object]]:
        """Run the simulation for up to ``days`` (or until completion)."""

        target = self.max_days if days is None else min(self.max_days, max(0, days))
        runs: list[dict[str, object]] = []
        for _ in range(target):
            if self.status != "running":
                break
            runs.append(self.run_day())
        return runs
