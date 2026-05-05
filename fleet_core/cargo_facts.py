from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from .fact_model import CargoFact, CargoFlightMetric, CargoManifestDetail, CraftFact, MissionFact, ObjectFact
from .normalizer import ROUTE_LOAD_STATUSES

CARGO_TRANSIT_KINDS = {"resource", "module", "crew_module", "fuel", "unknown"}


def sort_dt_key(value: datetime | None) -> datetime:
    return value if value else datetime.max


def cargo_kind_label(kind: str) -> str:
    return {
        "resource": "Resource",
        "module": "Module",
        "crew_module": "Crew module",
        "fuel": "Fuel",
        "unknown": "Unknown",
    }.get(kind, kind.replace("_", " ").title())


def object_label(object_facts: dict[int, ObjectFact], object_id: int | None) -> str:
    if object_id is None:
        return ""
    fact = object_facts.get(object_id)
    return fact.label if fact else f"Object {object_id}"


def build_cargo_flight_metrics(
    cargo_facts: list[CargoFact],
    mission_facts: list[MissionFact],
    craft_facts: list[CraftFact],
    object_facts: dict[int, ObjectFact],
) -> list[CargoFlightMetric]:
    missions = {mission.mission_key: mission for mission in mission_facts}
    craft_by_key = {(craft.company, craft.craft_id): craft for craft in craft_facts}
    groups: dict[str, dict[str, Any]] = {}

    for cargo in cargo_facts:
        if cargo.source_type != "mission" or cargo.mission_status not in ROUTE_LOAD_STATUSES:
            continue
        if cargo.cargo_kind not in CARGO_TRANSIT_KINDS:
            continue
        if cargo.mass <= 0:
            continue

        mission = missions.get(cargo.mission_key)
        mission_key = cargo.mission_key or cargo.source_key
        craft_ids = tuple(mission.craft_ids if mission else cargo.craft_ids)
        group = groups.setdefault(
            mission_key,
            {
                "mission_key": mission_key,
                "mission_id": mission.mission_id if mission else cargo.mission_id,
                "company": cargo.company,
                "status": mission.status if mission else cargo.mission_status,
                "craft_ids": set(craft_ids),
                "route": mission.route if mission else cargo.route,
                "source_id": mission.start_id if mission else None,
                "target_id": mission.target_id if mission else None,
                "departure": mission.departure if mission else cargo.departure,
                "arrival": mission.arrival if mission else cargo.arrival,
                "departure_dt": mission.departure_dt if mission else cargo.departure_dt,
                "arrival_dt": mission.arrival_dt if mission else cargo.arrival_dt,
                "total_tons": 0.0,
                "fuel_tons": 0.0,
                "colonization_support_tons": 0.0,
                "colonization_support_items": 0,
                "colonization_support_categories": defaultdict(float),
                "item_count": 0,
                "cargo_totals": defaultdict(float),
                "kind_counts": Counter(),
                "details": [],
            },
        )

        group["total_tons"] = float(group["total_tons"]) + cargo.mass
        if cargo.cargo_kind == "fuel":
            group["fuel_tons"] = float(group["fuel_tons"]) + cargo.mass
        if cargo.colonization_support_category:
            group["colonization_support_tons"] = float(group["colonization_support_tons"]) + cargo.mass
            group["colonization_support_items"] = int(group["colonization_support_items"]) + 1
            group["colonization_support_categories"][cargo.colonization_support_category] += cargo.mass
        group["item_count"] = int(group["item_count"]) + 1

        display_name = cargo.display_name or cargo_kind_label(cargo.cargo_kind)
        kind = cargo_kind_label(cargo.cargo_kind)
        group["cargo_totals"][display_name] += cargo.mass
        group["kind_counts"][kind] += 1
        group["details"].append(
            CargoManifestDetail(
                name=display_name,
                kind=kind,
                list_label=cargo.list_label,
                mass=cargo.mass,
                resource_key=cargo.resource_key,
                module_key=cargo.module_key,
                colonization_support_category=cargo.colonization_support_category,
                colonization_support_reason=cargo.colonization_support_reason,
            )
        )

    rows: list[CargoFlightMetric] = []
    for group in groups.values():
        company = str(group["company"])
        craft_ids = tuple(sorted(craft_id for craft_id in group["craft_ids"] if isinstance(craft_id, int)))
        craft_names = tuple(
            craft_by_key[(company, craft_id)].craft_name
            for craft_id in craft_ids
            if (company, craft_id) in craft_by_key
        )
        source_id = group["source_id"] if isinstance(group["source_id"], int) else None
        target_id = group["target_id"] if isinstance(group["target_id"], int) else None
        details = tuple(
            sorted(
                group["details"],
                key=lambda detail: (detail.kind, detail.name, detail.list_label, detail.mass),
            )
        )
        rows.append(
            CargoFlightMetric(
                flight_key=str(group["mission_key"]),
                mission_key=str(group["mission_key"]),
                mission_id=str(group["mission_id"]),
                company=company,
                status=str(group["status"]),
                craft_ids=craft_ids,
                craft_names=craft_names,
                route=str(group["route"]),
                source_id=source_id,
                target_id=target_id,
                source=object_label(object_facts, source_id),
                destination=object_label(object_facts, target_id),
                departure=str(group["departure"]),
                arrival=str(group["arrival"]),
                departure_dt=group["departure_dt"],
                arrival_dt=group["arrival_dt"],
                total_tons=float(group["total_tons"]),
                fuel_tons=float(group["fuel_tons"]),
                colonization_support_tons=float(group["colonization_support_tons"]),
                colonization_support_items=int(group["colonization_support_items"]),
                colonization_support_categories=tuple(
                    sorted(group["colonization_support_categories"].items(), key=lambda item: (-item[1], item[0]))
                ),
                item_count=int(group["item_count"]),
                cargo_totals=tuple(sorted(group["cargo_totals"].items(), key=lambda item: (-item[1], item[0]))),
                kind_counts=tuple(sorted(group["kind_counts"].items())),
                details=details,
            )
        )

    status_rank = {"En route": 0, "Cyclical": 1, "Planned": 2}
    return sorted(
        rows,
        key=lambda row: (
            status_rank.get(row.status, 9),
            sort_dt_key(row.arrival_dt),
            row.company,
            row.mission_id,
        ),
    )
