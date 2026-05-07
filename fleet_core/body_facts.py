from __future__ import annotations

from typing import Any

from .fact_model import BodyMetric, CargoFact, CraftFact, MissionFact, ObjectFact
from .normalizer_utils import ROUTE_ACTIVE_STATUSES, ROUTE_LOAD_STATUSES, ROUTE_PLANNED_STATUSES


def build_body_metrics(
    object_facts: dict[int, ObjectFact],
    craft_facts: list[CraftFact],
    cargo_facts: list[CargoFact] | None = None,
    mission_facts: list[MissionFact] | None = None,
) -> list[BodyMetric]:
    mission_by_key = {mission.mission_key: mission for mission in mission_facts or []}
    grouped: dict[int, dict[str, Any]] = {}

    def body_group(object_id: int) -> dict[str, Any]:
        fact = object_facts.get(object_id)
        return grouped.setdefault(
            object_id,
            {
                "object_id": object_id,
                "body": fact.label if fact else f"Object {object_id}",
                "object_type": fact.object_type if fact else "",
                "parent": fact.parent_label if fact else "",
                "relationship": fact.relationship if fact else "",
                "companies": set(fact.owner_companies if fact else ()),
                "craft_present": 0,
                "idle_craft": 0,
                "active_inbound_craft": 0,
                "planned_inbound_craft": 0,
                "outbound_craft": 0,
                "inbound_cargo": {},
                "inbound_people": 0,
                "outbound_people": 0,
                "next_arrival": "",
                "craft_here": [],
                "inbound_routes": [],
                "outbound_routes": [],
                "warnings": set(),
            },
        )

    def add_next_arrival(group: dict[str, Any], arrival: str) -> None:
        if arrival and (not group["next_arrival"] or arrival < group["next_arrival"]):
            group["next_arrival"] = arrival

    for craft in craft_facts:
        if craft.current_object_id is not None:
            group = body_group(craft.current_object_id)
            group["craft_present"] = int(group["craft_present"]) + 1
            if craft.status == "Idle":
                group["idle_craft"] = int(group["idle_craft"]) + 1
            group["craft_here"].append(f"{craft.craft_name} ({craft.status})")
            group["companies"].add(craft.company)
            if craft.warnings:
                group["warnings"].update(part.strip() for part in craft.warnings.split(";") if part.strip())

        if not craft.has_active_assignment:
            continue
        mission = mission_by_key.get(craft.active_assignment_key)
        if not mission:
            continue

        if mission.route_type == "cyclical":
            endpoints = [object_id for object_id in (mission.start_id, mission.target_id) if object_id is not None]
            for object_id in endpoints:
                group = body_group(object_id)
                group["outbound_craft"] = int(group["outbound_craft"]) + 1
                group["outbound_routes"].append(mission.route)
                group["inbound_routes"].append(mission.route)
                group["companies"].add(craft.company)
                if craft.status in ROUTE_ACTIVE_STATUSES:
                    group["active_inbound_craft"] = int(group["active_inbound_craft"]) + 1
                elif craft.status in ROUTE_PLANNED_STATUSES:
                    group["planned_inbound_craft"] = int(group["planned_inbound_craft"]) + 1
        else:
            if mission.start_id is not None:
                origin = body_group(mission.start_id)
                origin["outbound_craft"] = int(origin["outbound_craft"]) + 1
                origin["outbound_routes"].append(mission.route)
                origin["companies"].add(craft.company)
            if mission.target_id is not None:
                destination = body_group(mission.target_id)
                destination["inbound_routes"].append(mission.route)
                destination["companies"].add(craft.company)
                add_next_arrival(destination, craft.arrival)
                if craft.status in ROUTE_ACTIVE_STATUSES:
                    destination["active_inbound_craft"] = int(destination["active_inbound_craft"]) + 1
                elif craft.status in ROUTE_PLANNED_STATUSES:
                    destination["planned_inbound_craft"] = int(destination["planned_inbound_craft"]) + 1

    for cargo in cargo_facts or []:
        if cargo.source_type != "mission" or cargo.mission_status not in ROUTE_LOAD_STATUSES:
            continue
        mission = mission_by_key.get(cargo.mission_key)
        if not mission:
            continue
        if cargo.people > 0:
            if mission.start_id is not None:
                origin = body_group(mission.start_id)
                origin["outbound_people"] = int(origin["outbound_people"]) + cargo.people
            if mission.target_id is not None:
                destination = body_group(mission.target_id)
                destination["inbound_people"] = int(destination["inbound_people"]) + cargo.people

        if cargo.mass <= 0 or cargo.cargo_kind in {"fuel", "life_support", "unknown"}:
            continue
        if mission.target_id is not None:
            destination = body_group(mission.target_id)
            inbound_cargo = destination["inbound_cargo"]
            inbound_cargo[cargo.display_name] = float(inbound_cargo.get(cargo.display_name, 0.0)) + cargo.mass

    metrics: list[BodyMetric] = []
    for object_id, group in grouped.items():
        if not any(
            (
                group["craft_present"],
                group["active_inbound_craft"],
                group["planned_inbound_craft"],
                group["outbound_craft"],
                group["inbound_people"],
                group["outbound_people"],
                group["inbound_cargo"],
            )
        ):
            continue
        inbound_cargo = tuple(sorted((str(name), float(mass)) for name, mass in group["inbound_cargo"].items()))
        warnings = tuple(sorted(group["warnings"]))
        metrics.append(
            BodyMetric(
                object_id=object_id,
                body=str(group["body"]),
                object_type=str(group["object_type"]),
                parent=str(group["parent"]),
                relationship=str(group["relationship"]),
                companies=tuple(sorted(group["companies"])),
                craft_present=int(group["craft_present"]),
                idle_craft=int(group["idle_craft"]),
                active_inbound_craft=int(group["active_inbound_craft"]),
                planned_inbound_craft=int(group["planned_inbound_craft"]),
                outbound_craft=int(group["outbound_craft"]),
                inbound_cargo=inbound_cargo,
                inbound_people=int(group["inbound_people"]),
                outbound_people=int(group["outbound_people"]),
                next_arrival=str(group["next_arrival"] or ""),
                craft_here=tuple(group["craft_here"]),
                inbound_routes=tuple(sorted(set(group["inbound_routes"]))),
                outbound_routes=tuple(sorted(set(group["outbound_routes"]))),
                warnings=warnings,
            )
        )
    return sorted(metrics, key=lambda item: item.body)
