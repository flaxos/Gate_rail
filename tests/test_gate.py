"""Tests for gate slot allocation, condition, and wear."""

from gaterail.gate import WormholeGate


def test_transit_allowed_and_denied_by_slots_and_condition() -> None:
    gate = WormholeGate(max_slots_per_day=2, max_wear=10.0, wear=0.0)

    assert gate.can_allocate_slots(1)
    assert gate.allocate_slots(1)
    assert gate.allocate_slots(1)
    assert not gate.allocate_slots(1)

    gate.wear = gate.max_wear
    assert not gate.operational
    assert not gate.can_allocate_slots(1)
    assert not gate.allocate_slots(1)


def test_wear_is_applied_per_jump_and_capped() -> None:
    gate = WormholeGate(max_wear=5.0, wear_per_jump=1.5, wear=1.0)

    gate.apply_wear(2)
    assert gate.wear == 4.0

    gate.apply_wear(5)
    assert gate.wear == 5.0
    assert gate.condition == 0.0
