"""Stable player-facing identities for otherwise anonymous market assets."""

import uuid

_GATE_PREFIXES = (
    "Ashen",
    "Blackglass",
    "Cinder",
    "Eclipsed",
    "Gilded",
    "Hollow",
    "Iron",
    "Obsidian",
    "Runebound",
    "Silent",
    "Starless",
    "Umbral",
)

_GATE_SUFFIXES = (
    "Archive",
    "Bastion",
    "Choir",
    "Cradle",
    "Crown",
    "Deep",
    "Meridian",
    "Rift",
    "Sanctum",
    "Threshold",
    "Vault",
    "Wound",
)


def gate_ticker(gate_id: uuid.UUID, rank: str) -> str:
    """Return compact deterministic exchange ticker."""
    rank_label = "S+" if rank == "S_PLUS" else rank
    return f"DG-{rank_label}-{gate_id.hex[:6].upper()}"


def gate_display_name(gate_id: uuid.UUID) -> str:
    """Return deterministic lore name without storing presentation-only data."""
    seed = gate_id.int
    prefix = _GATE_PREFIXES[seed % len(_GATE_PREFIXES)]
    suffix = _GATE_SUFFIXES[(seed // len(_GATE_PREFIXES)) % len(_GATE_SUFFIXES)]
    return f"{prefix} {suffix}"
