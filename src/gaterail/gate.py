"""Wormhole gate model and condition/slot logic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WormholeGate:
    """Transit gate with finite daily throughput and wear."""

    name: str = "Primary Gate"
    max_slots_per_day: int = 12
    wear: float = 0.0
    wear_per_jump: float = 0.8
    max_wear: float = 100.0
    base_daily_cost: float = 240.0
    cost_per_wear_point: float = 1.4
    slots_used_today: int = 0

    def reset_daily_slots(self) -> None:
        """Reset slot usage for new day."""

        self.slots_used_today = 0

    @property
    def slots_remaining(self) -> int:
        """Transit slots available today."""

        return max(0, self.max_slots_per_day - self.slots_used_today)

    @property
    def condition(self) -> float:
        """Gate health as a 0..1 ratio."""

        if self.max_wear <= 0:
            return 0.0
        return max(0.0, 1.0 - (self.wear / self.max_wear))

    @property
    def operational(self) -> bool:
        """Whether gate can accept transits."""

        return self.condition > 0.0

    def can_allocate_slots(self, count: int = 1) -> bool:
        """Return whether ``count`` additional slots can be reserved."""

        return self.operational and count >= 0 and self.slots_remaining >= count

    def allocate_slots(self, count: int = 1) -> bool:
        """Reserve ``count`` slots if possible."""

        if not self.can_allocate_slots(count):
            return False
        self.slots_used_today += count
        return True

    def apply_wear(self, jumps: int) -> None:
        """Apply wear accumulated from gate jumps."""

        if jumps <= 0:
            return
        self.wear = min(self.max_wear, self.wear + jumps * self.wear_per_jump)

    def daily_operating_cost(self) -> float:
        """Operating cost grows with accumulated wear."""

        return self.base_daily_cost + (self.wear * self.cost_per_wear_point)
