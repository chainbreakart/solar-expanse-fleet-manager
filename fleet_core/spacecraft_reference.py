from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

SPACECRAFT_HEAD_NAME_RE = re.compile(r"^Spacecraft\d+(.+)$")
CAPACITY_SEMANTICS_NORMAL = "normal"
CAPACITY_SEMANTICS_ORBITAL_PAYLOAD_CONTAINER = "launch_limited_upward_unlimited_downward"
ORBITAL_PAYLOAD_CONTAINER_TYPES = {"spacecraft_capsule"}

SPACECRAFT_TYPE_HULL_CANDIDATES: dict[str, tuple[str, ...]] = {
    "spacecraft_chem_small": ("Iris",),
    "spacecraft_chem_mid2": ("Selene", "Orion", "Orion Hull"),
    "spacecraft_chem_large": ("Helios Hull", "Stratos"),
    "spacecraft_electric_small": ("Hermes Hull", "Hermes"),
    "spacecraft_electric_mid": ("Hecate Hull", "Athena", "Hecate"),
    "spacecraft_nuke_small": ("Prometheus Hull", "Prometheus"),
    "spacecraft_nuke_mid": ("Hull Enter", "Hephaistos Hull", "Hephaistos"),
    "spacecraft_nuke_large": ("Ariane Hull", "Ariane"),
    "spacecraft_nuke_nolv": ("Cronos Hull", "Cronos"),
    "spacecraft_sail_small": ("Solar Hull", "Daedalus"),
    "spacecraft_sail_mid": ("Talos Hull", "Talos"),
    "spacecraft_sail_long": ("Zephyr Hull", "Zephyr"),
    "spacecraft_fusion_small": ("Nike Hull", "Nike"),
    "spacecraft_fusion_mid": ("Sirius Hull", "Sirius"),
    "spacecraft_fusion_large": ("Zeus Hull", "Zeus"),
}


def load_reference_maps(repo_root: Path) -> tuple[dict[str, str], dict[str, str]]:
    buildables: dict[str, str] = {}
    resources: dict[str, str] = {}

    buildables_path = repo_root / "generated_data" / "data_buildables.csv"
    if buildables_path.exists():
        with buildables_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                name = row.get("buildable_name", "")
                for key in (row.get("game_key", ""), *(row.get("candidate_game_keys", "") or "").split(";")):
                    key = key.strip()
                    if key and name:
                        buildables[key] = name

    resources_path = repo_root / "data" / "derived" / "population" / "resources.csv"
    if resources_path.exists():
        with resources_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("resource_id") and row.get("resource_name"):
                    resources[row["resource_id"]] = row["resource_name"]

    return buildables, resources


def load_spacecraft_stats(repo_root: Path) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    path = repo_root / "generated_data" / "spacecraft_base_reference.csv"
    if not path.exists():
        return stats

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            game_id = row.get("game_id", "")
            if not game_id:
                continue

            def float_field(name: str) -> float | None:
                raw = row.get(name, "")
                if raw in {"", None}:
                    return None
                try:
                    return float(raw)
                except ValueError:
                    return None

            asset_name = row.get("asset_name") or game_id
            head_name = row.get("head_name") or ""
            stats[game_id] = {
                "asset_name": asset_name,
                "category": row.get("category") or "",
                "head_name": head_name,
                "hull_candidates": spacecraft_hull_candidates(game_id, asset_name, head_name),
                "cargo_capacity_t": float_field("cargo_capacity_t"),
                "fuel_capacity_t": float_field("fuel_capacity_t"),
                "propulsion_class": row.get("propulsion_class") or "",
                "fuel_type_id": row.get("engine_fuel_type_id") or "",
                "fuel_type_name": row.get("engine_fuel_type_name") or "",
                "surface_capable": (row.get("surface_capable") or "").lower() == "true",
                "orbit_only": (row.get("orbit_only") or "").lower() == "true",
                "construction_mode": row.get("construction_mode") or "",
                "continuous_burn_capable": (row.get("continuous_burn_capable") or "").lower() == "true",
                "capacity_semantics": capacity_semantics_for_spacecraft(game_id),
            }
    return stats


def spacecraft_hull_candidates(game_id: str, asset_name: str, head_name: str) -> tuple[str, ...]:
    candidates: list[str] = []

    def add(value: str) -> None:
        clean = value.strip()
        if clean and clean not in candidates:
            candidates.append(clean)
            if not clean.lower().endswith("hull"):
                candidates.append(f"{clean} Hull")

    for value in (asset_name, head_name, game_id):
        add(value)
    head_match = SPACECRAFT_HEAD_NAME_RE.match(head_name)
    if head_match:
        add(head_match.group(1))
    return tuple(candidates)


def capacity_semantics_for_spacecraft(game_id: str) -> str:
    if game_id in ORBITAL_PAYLOAD_CONTAINER_TYPES:
        return CAPACITY_SEMANTICS_ORBITAL_PAYLOAD_CONTAINER
    return CAPACITY_SEMANTICS_NORMAL
