"""Tests for R19 rail signals and protected block dispatch."""

from __future__ import annotations

import pytest

from gaterail.cargo import CargoType
from gaterail.commands import command_from_dict
from gaterail.models import (
    DevelopmentTier,
    FreightOrder,
    FreightTrain,
    GameState,
    LinkMode,
    NetworkLink,
    NetworkNode,
    NodeKind,
    TrackSignal,
    TrackSignalKind,
    TrainStatus,
    WorldState,
)
from gaterail.persistence import state_from_dict, state_to_dict
from gaterail.reporting import format_scenario_inspection, format_tick_report
from gaterail.scenarios import build_sprint8_scenario
from gaterail.simulation import TickSimulation
from gaterail.snapshot import render_snapshot


def _signal_test_state(*, with_signal: bool = True) -> GameState:
    """Build a two-train rail block scenario."""

    state = GameState()
    state.add_world(
        WorldState(
            id="test_world",
            name="Test World",
            tier=DevelopmentTier.OUTPOST,
            power_available=100,
        )
    )
    state.add_node(
        NetworkNode(
            id="origin_yard",
            name="Origin Yard",
            world_id="test_world",
            kind=NodeKind.DEPOT,
            inventory={CargoType.FOOD: 100},
            storage_capacity=1_000,
            transfer_limit_per_tick=100,
        )
    )
    state.add_node(
        NetworkNode(
            id="destination_yard",
            name="Destination Yard",
            world_id="test_world",
            kind=NodeKind.WAREHOUSE,
            storage_capacity=1_000,
            transfer_limit_per_tick=100,
        )
    )
    state.add_link(
        NetworkLink(
            id="rail_origin_destination",
            origin="origin_yard",
            destination="destination_yard",
            mode=LinkMode.RAIL,
            travel_ticks=2,
            capacity_per_tick=2,
        )
    )
    state.add_train(FreightTrain(id="train_a", name="Atlas", node_id="origin_yard", capacity=10))
    state.add_train(FreightTrain(id="train_b", name="Boreas", node_id="origin_yard", capacity=10))
    state.add_order(
        FreightOrder(
            id="order_a",
            train_id="train_a",
            origin="origin_yard",
            destination="destination_yard",
            cargo_type=CargoType.FOOD,
            requested_units=10,
            priority=200,
        )
    )
    state.add_order(
        FreightOrder(
            id="order_b",
            train_id="train_b",
            origin="origin_yard",
            destination="destination_yard",
            cargo_type=CargoType.FOOD,
            requested_units=10,
            priority=100,
        )
    )
    if with_signal:
        state.add_track_signal(
            TrackSignal(
                id="origin_departure_stop",
                link_id="rail_origin_destination",
                kind=TrackSignalKind.STOP,
                node_id="origin_yard",
            )
        )
    return state


def test_signaled_rail_block_queues_second_departure_before_loading() -> None:
    simulation = TickSimulation(state=_signal_test_state(with_signal=True))

    report = simulation.step_tick()

    assert [event["train"] for event in report["freight"]["dispatches"]] == ["Atlas"]
    assert simulation.state.nodes["origin_yard"].stock(CargoType.FOOD) == 90
    assert simulation.state.trains["train_b"].status == TrainStatus.IDLE
    assert {
        "train": "Boreas",
        "order": "order_b",
        "origin": "origin_yard",
        "destination": "destination_yard",
        "link": "rail_origin_destination",
        "reason": "signal block occupied on rail_origin_destination by train_a",
    } in report["freight"]["queued"]
    assert {
        "link": "rail_origin_destination",
        "severity": "signal_blocked",
        "reason": "signal block occupied on rail_origin_destination by train_a",
        "capacity": 1,
        "used": 1,
    } in report["traffic"]["alerts"]
    assert report["signals"]["blocks"]["rail_origin_destination"]["occupiers"] == ["train_a"]
    assert report["signals"]["blocked"] == [
        {
            "link": "rail_origin_destination",
            "block": "rail_origin_destination",
            "train_id": "train_b",
            "occupiers": ["train_a"],
            "signal_ids": ["origin_departure_stop"],
            "reason": "signal block occupied on rail_origin_destination by train_a",
        }
    ]


def test_unsignaled_rail_link_keeps_existing_capacity_behavior() -> None:
    simulation = TickSimulation(state=_signal_test_state(with_signal=False))

    report = simulation.step_tick()

    assert [event["train"] for event in report["freight"]["dispatches"]] == ["Atlas", "Boreas"]
    assert report["freight"]["queued"] == []
    assert simulation.state.nodes["origin_yard"].stock(CargoType.FOOD) == 80
    assert report["signals"]["blocks"] == {}


def test_signaled_block_stays_occupied_until_in_transit_train_arrives() -> None:
    simulation = TickSimulation(state=_signal_test_state(with_signal=True))

    simulation.step_tick()
    second = simulation.step_tick()
    third = simulation.step_tick()

    assert second["freight"]["queued"][0]["reason"] == (
        "signal block occupied on rail_origin_destination by train_a"
    )
    assert not any(event["train"] == "Boreas" for event in second["freight"]["dispatches"])
    assert any(event["train"] == "Boreas" for event in third["freight"]["dispatches"])


def test_track_signals_persist_snapshot_and_build_from_command() -> None:
    state = _signal_test_state(with_signal=False)

    preview = state.apply_command(
        command_from_dict(
            {
                "type": "PreviewBuildTrackSignal",
                "signal_id": "destination_path",
                "link_id": "rail_origin_destination",
                "node_id": "destination_yard",
                "kind": "path",
            }
        )
    )
    assert preview["ok"] is True
    assert preview["normalized_command"] == {
        "type": "BuildTrackSignal",
        "signal_id": "destination_path",
        "link_id": "rail_origin_destination",
        "kind": "path",
        "node_id": "destination_yard",
        "active": True,
    }

    result = state.apply_command(command_from_dict(preview["normalized_command"]))

    assert result["ok"] is True
    assert state.track_signals["destination_path"].kind == TrackSignalKind.PATH

    restored = state_from_dict(state_to_dict(state))
    assert restored.track_signals["destination_path"] == state.track_signals["destination_path"]

    snapshot = render_snapshot(restored)
    assert snapshot["track_signals"] == [
        {
            "id": "destination_path",
            "link": "rail_origin_destination",
            "node": "destination_yard",
            "kind": "path",
            "active": True,
            "block": "rail_origin_destination",
        }
    ]
    assert snapshot["rail_blocks"] == [
        {
            "link": "rail_origin_destination",
            "block": "rail_origin_destination",
            "signal_ids": ["destination_path"],
            "occupied": False,
            "occupiers": [],
            "reserved_by": None,
        }
    ]
    link = next(item for item in snapshot["links"] if item["id"] == "rail_origin_destination")
    assert link["signals"] == ["destination_path"]


def test_track_signal_validation_rejects_non_rail_target() -> None:
    state = build_sprint8_scenario()

    with pytest.raises(ValueError, match="target link is not rail"):
        state.add_track_signal(
            TrackSignal(
                id="bad_gate_signal",
                link_id="gate_core_frontier",
                kind=TrackSignalKind.STOP,
                node_id="core_gate",
            )
        )


def test_signal_text_reports_show_blocks_and_waiting_reason() -> None:
    simulation = TickSimulation(state=_signal_test_state(with_signal=True))

    inspection = format_scenario_inspection(simulation.state, {"signals"})
    report = simulation.step_tick()
    tick_text = format_tick_report(report, {"signals", "traffic", "freight"})

    assert "Track Signals" in inspection
    assert "origin_departure_stop" in inspection
    assert "Rail Blocks" in inspection
    assert "Signals: blocked train_b on rail_origin_destination" in tick_text
    assert "signal_blocked rail_origin_destination" in tick_text
