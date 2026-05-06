"""Backend-owned rules for local operational construction helpers."""

from __future__ import annotations

from dataclasses import dataclass

from gaterail.cargo import CargoType
from gaterail.models import FacilityComponent, FacilityPort, TransferLinkKind


_BULK_CARGO: frozenset[CargoType] = frozenset(
    {
        CargoType.ORE,
        CargoType.CARBON_FEEDSTOCK,
        CargoType.STONE,
        CargoType.URANIUM,
        CargoType.METAL,
    }
)
_FLUID_CARGO: frozenset[CargoType] = frozenset(
    {
        CargoType.WATER,
        CargoType.FUEL,
        CargoType.COOLANT,
    }
)
_PROTECTED_CARGO: frozenset[CargoType] = frozenset(
    {
        CargoType.ELECTRONICS,
        CargoType.MEDICAL_SUPPLIES,
        CargoType.RESEARCH_EQUIPMENT,
        CargoType.REACTOR_PARTS,
        CargoType.GATE_COMPONENTS,
    }
)


@dataclass(frozen=True, slots=True)
class TransferLinkProfile:
    """One backend transfer-link profile for validation and simulation."""

    link_type: TransferLinkKind
    label: str
    cargo_classes: tuple[str, ...]
    allowed_cargo: frozenset[CargoType] | None = None
    rate_multiplier: float = 1.0


TRANSFER_LINK_PROFILES: dict[TransferLinkKind, TransferLinkProfile] = {
    TransferLinkKind.CONVEYOR: TransferLinkProfile(
        link_type=TransferLinkKind.CONVEYOR,
        label="Conveyor",
        cargo_classes=("general",),
    ),
    TransferLinkKind.HOPPER: TransferLinkProfile(
        link_type=TransferLinkKind.HOPPER,
        label="Bulk hopper",
        cargo_classes=("bulk",),
        allowed_cargo=_BULK_CARGO,
        rate_multiplier=1.5,
    ),
    TransferLinkKind.PIPE: TransferLinkProfile(
        link_type=TransferLinkKind.PIPE,
        label="Pipe",
        cargo_classes=("fluid",),
        allowed_cargo=_FLUID_CARGO,
        rate_multiplier=2.0,
    ),
    TransferLinkKind.VAC_TUBE: TransferLinkProfile(
        link_type=TransferLinkKind.VAC_TUBE,
        label="Vac tube",
        cargo_classes=("protected", "general"),
        allowed_cargo=_PROTECTED_CARGO | _FLUID_CARGO | _BULK_CARGO,
        rate_multiplier=1.25,
    ),
    TransferLinkKind.MAG_TUBE: TransferLinkProfile(
        link_type=TransferLinkKind.MAG_TUBE,
        label="Mag tube",
        cargo_classes=("heavy", "protected"),
        allowed_cargo=_PROTECTED_CARGO
        | {
            CargoType.MACHINERY,
            CargoType.PARTS,
            CargoType.CONSTRUCTION_MATERIALS,
            CargoType.GATE_COMPONENTS,
        },
        rate_multiplier=1.25,
    ),
}


def transfer_link_profile(kind: TransferLinkKind | str) -> TransferLinkProfile:
    """Return one transfer-link profile, accepting string command values."""

    link_type = kind if isinstance(kind, TransferLinkKind) else TransferLinkKind(str(kind))
    return TRANSFER_LINK_PROFILES[link_type]


def transfer_link_profile_payload(kind: TransferLinkKind | str) -> dict[str, object]:
    """Return JSON-safe profile data for clients."""

    profile = transfer_link_profile(kind)
    return {
        "link_type": profile.link_type.value,
        "label": profile.label,
        "cargo_classes": list(profile.cargo_classes),
        "allowed_cargo": (
            []
            if profile.allowed_cargo is None
            else [cargo.value for cargo in sorted(profile.allowed_cargo, key=lambda item: item.value)]
        ),
        "rate_multiplier": profile.rate_multiplier,
    }


def transfer_link_profiles_payload() -> list[dict[str, object]]:
    """Return every transfer-link profile in stable order."""

    return [
        transfer_link_profile_payload(kind)
        for kind in sorted(TRANSFER_LINK_PROFILES, key=lambda item: item.value)
    ]


def transfer_link_supports_cargo(kind: TransferLinkKind | str, cargo_type: CargoType) -> bool:
    """Return whether a transfer-link kind may move the given cargo."""

    allowed = transfer_link_profile(kind).allowed_cargo
    return allowed is None or cargo_type in allowed


def transfer_link_rate_multiplier(kind: TransferLinkKind | str) -> float:
    """Return the backend movement-rate multiplier for a transfer-link kind."""

    return transfer_link_profile(kind).rate_multiplier


def infer_connection_cargo(
    source_component: FacilityComponent,
    source_port: FacilityPort,
    destination_component: FacilityComponent,
    destination_port: FacilityPort,
) -> CargoType | None:
    """Infer the single cargo type a connection should move."""

    if source_port.cargo_type is not None:
        return source_port.cargo_type
    if destination_port.cargo_type is not None:
        return destination_port.cargo_type
    source_outputs = set(source_component.outputs)
    destination_inputs = set(destination_component.inputs)
    matches = sorted(source_outputs & destination_inputs, key=lambda item: item.value)
    if len(matches) == 1:
        return matches[0]
    if len(destination_inputs) == 1:
        return next(iter(destination_inputs))
    if len(source_outputs) == 1:
        return next(iter(source_outputs))
    return None
