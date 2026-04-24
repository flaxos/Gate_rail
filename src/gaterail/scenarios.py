"""Scenario definitions and factory helpers for GateRail."""

from __future__ import annotations

from dataclasses import dataclass

from gaterail.colony import Colony
from gaterail.finance import CorporateFinance
from gaterail.gate import WormholeGate
from gaterail.simulation import Simulation
from gaterail.train import Train
from gaterail.world import World


@dataclass(frozen=True, slots=True)
class Scenario:
    """Configuration bundle used to initialize a simulation run."""

    name: str
    world: World
    gate: WormholeGate
    trains: list[Train]
    colony: Colony
    finance: CorporateFinance
    max_days: int = 365

    def create_simulation(self) -> Simulation:
        """Build a Simulation instance from this scenario."""

        return Simulation(
            world=self.world,
            gate=self.gate,
            trains=self.trains,
            colony=self.colony,
            finance=self.finance,
            max_days=self.max_days,
        )


def new_carthage_gate_contract() -> Scenario:
    """Default scenario configured with baseline starting values."""

    return Scenario(
        name="New Carthage Gate Contract",
        world=World.default(),
        gate=WormholeGate(),
        trains=[Train(name="Atlas"), Train(name="Nova", capacity=16)],
        colony=Colony(),
        finance=CorporateFinance(),
        max_days=365,
    )


def default_scenario() -> Scenario:
    """Return the repository default scenario."""

    return new_carthage_gate_contract()
