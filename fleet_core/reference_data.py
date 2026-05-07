from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from .fact_model import TechReferenceCatalog, TechReferenceModifier, TechReferenceRow
from .normalizer_utils import friendly_key


REPO_GENERATED_DATA = "generated_data"
POPULATION_DATA = "data/derived/population"
SUPPLY_TECH_MODIFIERS = "data/derived/population/supply_technology_modifiers.csv"
SPACECRAFT_MODIFIER_COLUMNS: tuple[tuple[str, str], ...] = (
    ("cargo_capacity_t", "cargo_capacity_t"),
    ("fuel_capacity_t", "fuel_capacity_t"),
    ("dry_mass_t", "dry_mass_t"),
    ("thrust", "thrust"),
    ("exhaust_velocity", "exhaust_velocity"),
    ("build_days", "build_days"),
    ("maintenance_per_day", "maintenance_per_day"),
    ("reusability", "reusability"),
)
SPACECRAFT_GLOBAL_BONUS_ROWS: tuple[tuple[str, str, str, str, float], ...] = (
    ("research_sc_cargo1", "Cargo Capacity I", "component_cargo_capacity_percent", "All", 50.0),
    ("research_sc_cargo2", "Cargo Capacity II", "component_cargo_capacity_percent", "All", 50.0),
    ("research_sc_cargo3", "Cargo Capacity III", "component_cargo_capacity_percent", "All", 50.0),
    ("research_sc_cargo4", "Cargo Capacity IV", "component_cargo_capacity_percent", "All", 50.0),
)


def split_semicolon(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(";") if part.strip())


def as_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def title_from_research_id(research_id: str) -> str:
    if research_id.startswith("research_sc_"):
        return research_id.removeprefix("research_sc_").replace("_", " ").strip().title()
    return friendly_key(research_id)


def category_from_research_id(research_id: str, fallback: str = "Research") -> str:
    if fallback and fallback != "Research":
        return fallback
    prefixes = (
        ("research_sc_", "Spacecraft"),
        ("research_sails", "Spacecraft"),
        ("research_lv", "Launch"),
        ("research_launch", "Launch"),
        ("research_lifesup", "Lifesup"),
        ("research_agriculture", "Agriculture"),
        ("research_biotech", "Biotech"),
        ("research_terraforming", "Terraforming"),
        ("research_robotics", "Robotics"),
    )
    for prefix, category in prefixes:
        if research_id.startswith(prefix):
            return category
    return fallback


def classify_unlock_targets(targets: tuple[str, ...], spacecraft_ids: set[str]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    spacecraft: list[str] = []
    facilities: list[str] = []
    modules: list[str] = []
    resources: list[str] = []
    for target in targets:
        if target in spacecraft_ids or target.startswith("spacecraft_"):
            spacecraft.append(target)
        elif target.startswith("module_"):
            modules.append(target)
        elif target.startswith("id_resource_"):
            resources.append(target)
        elif target.startswith("build_"):
            facilities.append(target)
    return tuple(spacecraft), tuple(facilities), tuple(modules), tuple(resources)


def merge_reference_row(existing: TechReferenceRow | None, incoming: TechReferenceRow) -> TechReferenceRow:
    if existing is None:
        return incoming

    def merged(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*left, *right)))

    title = existing.title if existing.title and existing.title != existing.research_id else incoming.title
    category = existing.category if existing.category and existing.category != "Research" else incoming.category
    confidence = "high" if "high" in {existing.confidence, incoming.confidence} else existing.confidence
    return replace(
        existing,
        title=title,
        category=category,
        prerequisite_chain=merged(existing.prerequisite_chain, incoming.prerequisite_chain),
        unlocked_spacecraft=merged(existing.unlocked_spacecraft, incoming.unlocked_spacecraft),
        unlocked_facilities=merged(existing.unlocked_facilities, incoming.unlocked_facilities),
        unlocked_modules=merged(existing.unlocked_modules, incoming.unlocked_modules),
        unlocked_resources=merged(existing.unlocked_resources, incoming.unlocked_resources),
        source="; ".join(dict.fromkeys((*existing.source.split("; "), incoming.source))),
        confidence=confidence,
    )


def add_reference_row(rows: dict[str, TechReferenceRow], incoming: TechReferenceRow) -> None:
    rows[incoming.research_id] = merge_reference_row(rows.get(incoming.research_id), incoming)


def load_transport_capacities(repo_root: Path) -> dict[str, dict[str, object]]:
    capacities: dict[str, dict[str, object]] = {}
    path = repo_root / "data" / "derived" / "population" / "habitat_capacities.csv"
    if not path.exists():
        return capacities

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("context") != "Transport":
                continue
            key = row.get("game_key") or ""
            try:
                capacity = int(float(row.get("capacity_per_unit") or 0))
            except ValueError:
                capacity = 0
            if key and capacity > 0:
                capacities[key] = {
                    "display_name": row.get("display_name") or friendly_key(key),
                    "capacity": capacity,
                }
    return capacities


def load_spacecraft_technology_reference(
    repo_root: Path,
    rows: dict[str, TechReferenceRow],
    modifiers: list[TechReferenceModifier],
) -> set[str]:
    spacecraft_ids: set[str] = set()
    path = repo_root / REPO_GENERATED_DATA / "spacecraft_base_reference.csv"
    if not path.exists():
        return spacecraft_ids

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            game_id = row.get("game_id") or ""
            if game_id:
                spacecraft_ids.add(game_id)
            research_id = row.get("research_id") or ""
            if not research_id:
                continue
            title = row.get("asset_name") or title_from_research_id(research_id)
            category = row.get("category") or category_from_research_id(research_id, "Spacecraft")
            add_reference_row(
                rows,
                TechReferenceRow(
                    research_id=research_id,
                    title=title,
                    category=category,
                    prerequisite_chain=(),
                    unlocked_spacecraft=(game_id,) if game_id else (),
                    unlocked_facilities=(),
                    unlocked_modules=(),
                    unlocked_resources=(),
                    source=str(path.relative_to(repo_root)),
                    confidence="high" if row.get("research_status") == "mapped" else "medium",
                ),
            )
            for column, modifier_type in SPACECRAFT_MODIFIER_COLUMNS:
                raw_value = row.get(column) or ""
                numeric = as_float(raw_value)
                if raw_value == "":
                    continue
                modifiers.append(
                    TechReferenceModifier(
                        research_id=research_id,
                        title=title,
                        category=category,
                        target_type="spacecraft",
                        target_key=game_id,
                        modifier_type=modifier_type,
                        raw_value=raw_value,
                        numeric_value=numeric,
                        multiplier=None,
                        source=str(path.relative_to(repo_root)),
                        confidence="high",
                    )
                )
    for research_id, title, modifier_type, target_key, percent in SPACECRAFT_GLOBAL_BONUS_ROWS:
        add_reference_row(
            rows,
            TechReferenceRow(
                research_id=research_id,
                title=title,
                category="Spacecraft",
                prerequisite_chain=(),
                unlocked_spacecraft=(),
                unlocked_facilities=(),
                unlocked_modules=(),
                unlocked_resources=(),
                source="bundled spacecraft capacity bonus reference",
                confidence="medium",
            ),
        )
        modifiers.append(
            TechReferenceModifier(
                research_id=research_id,
                title=title,
                category="Spacecraft",
                target_type="spacecraft",
                target_key=target_key,
                modifier_type=modifier_type,
                raw_value=f"{percent:g}",
                numeric_value=percent,
                multiplier=1.0 + percent / 100.0,
                source="bundled spacecraft capacity bonus reference",
                confidence="medium",
            )
        )
    return spacecraft_ids


def prerequisite_chain_from_population_rows(rows: list[dict[str, str]], current: dict[str, str]) -> tuple[str, ...]:
    family = current.get("family") or ""
    sequence = as_float(current.get("sequence"))
    if not family or sequence is None:
        return ()
    previous = [
        row.get("research_id") or ""
        for row in rows
        if row.get("family") == family
        and (prev_sequence := as_float(row.get("sequence"))) is not None
        and prev_sequence < sequence
        and row.get("research_id")
    ]
    return tuple(previous)


def load_population_technology_reference(
    repo_root: Path,
    rows: dict[str, TechReferenceRow],
    modifiers: list[TechReferenceModifier],
    spacecraft_ids: set[str],
) -> None:
    research_path = repo_root / POPULATION_DATA / "research_population.csv"
    if research_path.exists():
        with research_path.open(newline="", encoding="utf-8") as fh:
            research_rows = list(csv.DictReader(fh))
        for row in research_rows:
            research_id = row.get("research_id") or ""
            if not research_id:
                continue
            targets = split_semicolon(row.get("unlock_targets"))
            spacecraft, facilities, modules, resources = classify_unlock_targets(targets, spacecraft_ids)
            add_reference_row(
                rows,
                TechReferenceRow(
                    research_id=research_id,
                    title=row.get("title") or title_from_research_id(research_id),
                    category=row.get("family") or category_from_research_id(research_id),
                    prerequisite_chain=prerequisite_chain_from_population_rows(research_rows, row),
                    unlocked_spacecraft=spacecraft,
                    unlocked_facilities=facilities,
                    unlocked_modules=modules,
                    unlocked_resources=resources,
                    source=str(research_path.relative_to(repo_root)),
                    confidence="medium" if row.get("notes") else "high",
                ),
            )

    capacity_path = repo_root / POPULATION_DATA / "habitat_capacities.csv"
    if not capacity_path.exists():
        return
    with capacity_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            research_id = row.get("unlock_research_id") or ""
            target_key = row.get("game_key") or ""
            if not research_id or not target_key:
                continue
            title = row.get("unlock_research_title") or rows.get(research_id, TechReferenceRow(research_id, "", "", (), (), (), (), (), "", "")).title
            category = rows.get(research_id).category if research_id in rows else category_from_research_id(research_id)
            target_type = "module" if target_key.startswith("module_") else "facility"
            modifiers.append(
                TechReferenceModifier(
                    research_id=research_id,
                    title=title or title_from_research_id(research_id),
                    category=category,
                    target_type=target_type,
                    target_key=target_key,
                    modifier_type="population_capacity_per_unit",
                    raw_value=row.get("capacity_per_unit") or "",
                    numeric_value=as_float(row.get("capacity_per_unit")),
                    multiplier=None,
                    source=str(capacity_path.relative_to(repo_root)),
                    confidence="high",
                )
            )


def parse_supply_bonus(value: str) -> tuple[float | None, float | None]:
    match = re.search(r"([+-])(\d+(?:\.\d+)?)%", value)
    if not match:
        return None, None
    sign = 1.0 if match.group(1) == "+" else -1.0
    percent = sign * float(match.group(2))
    multiplier = 1.0 + percent / 100.0
    return percent, multiplier


def load_supply_technology_modifiers(
    repo_root: Path,
    rows: dict[str, TechReferenceRow],
    modifiers: list[TechReferenceModifier],
) -> None:
    path = repo_root / SUPPLY_TECH_MODIFIERS
    if not path.exists():
        return

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            research_id = row.get("research_id") or ""
            title = row.get("title") or title_from_research_id(research_id)
            category = row.get("category") or category_from_research_id(research_id)
            target_type = row.get("target_type") or ""
            target = row.get("target_key") or ""
            modifier_type = row.get("modifier_type") or ""
            bonus = row.get("bonus") or ""
            percent, multiplier = parse_supply_bonus(bonus)
            confidence = row.get("confidence") or "medium"
            if not research_id or not target_type or not target or not modifier_type:
                continue
            add_reference_row(
                rows,
                TechReferenceRow(
                    research_id=research_id,
                    title=title,
                    category=category,
                    prerequisite_chain=(),
                    unlocked_spacecraft=(),
                    unlocked_facilities=(),
                    unlocked_modules=(),
                    unlocked_resources=(),
                    source=str(path.relative_to(repo_root)),
                    confidence=confidence,
                ),
            )
            modifiers.append(
                TechReferenceModifier(
                    research_id=research_id,
                    title=title,
                    category=category,
                    target_type=target_type,
                    target_key=target,
                    modifier_type=modifier_type,
                    raw_value=bonus,
                    numeric_value=percent,
                    multiplier=multiplier,
                    source=str(path.relative_to(repo_root)),
                    confidence=confidence,
                )
            )


def load_technology_reference_catalog(repo_root: Path) -> TechReferenceCatalog:
    rows: dict[str, TechReferenceRow] = {}
    modifiers: list[TechReferenceModifier] = []
    spacecraft_ids = load_spacecraft_technology_reference(repo_root, rows, modifiers)
    load_population_technology_reference(repo_root, rows, modifiers, spacecraft_ids)
    load_supply_technology_modifiers(repo_root, rows, modifiers)

    sorted_rows = tuple(sorted(rows.values(), key=lambda row: (row.category, row.title, row.research_id)))
    sorted_modifiers = tuple(
        sorted(
            modifiers,
            key=lambda row: (row.category, row.title, row.research_id, row.target_type, row.target_key, row.modifier_type),
        )
    )
    by_modifier: dict[str, list[TechReferenceModifier]] = defaultdict(list)
    for modifier in sorted_modifiers:
        by_modifier[modifier.research_id].append(modifier)
    return TechReferenceCatalog(
        rows=sorted_rows,
        modifiers=sorted_modifiers,
        by_research_id={row.research_id: row for row in sorted_rows},
        modifiers_by_research_id={key: tuple(value) for key, value in by_modifier.items()},
    )
