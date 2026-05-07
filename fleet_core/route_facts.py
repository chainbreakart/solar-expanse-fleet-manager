from __future__ import annotations

from typing import Any

from .fact_model import CargoFact, CraftFact, RouteMetric
from .normalizer_utils import ROUTE_ACTIVE_STATUSES, ROUTE_LOAD_STATUSES, ROUTE_PLANNED_STATUSES


def build_route_metrics(
    craft_facts: list[CraftFact],
    cargo_facts: list[CargoFact] | None = None,
) -> list[RouteMetric]:
    grouped: dict[str, dict[str, Any]] = {}

    def route_group(route: str, route_type: str) -> dict[str, Any]:
        return grouped.setdefault(
            route,
            {
                "route": route,
                "route_type": route_type,
                "total_craft_count": 0,
                "active_craft_count": 0,
                "planned_craft_count": 0,
                "cargo_tons_in_transit": 0.0,
                "people_in_transit": 0,
                "next_departure": "",
                "next_arrival": "",
                "companies": set(),
                "status_counts": {},
                "assigned_craft": [],
                "cargo_summaries": [],
                "fuel_plan_summaries": [],
                "capacity_summaries": [],
                "transfers": set(),
                "warnings": set(),
            },
        )

    for craft in craft_facts:
        if not craft.has_active_assignment or not craft.route:
            continue
        group = route_group(craft.route, craft.route_type)
        group["total_craft_count"] = int(group["total_craft_count"]) + 1
        if craft.status in ROUTE_ACTIVE_STATUSES:
            group["active_craft_count"] = int(group["active_craft_count"]) + 1
        if craft.status in ROUTE_LOAD_STATUSES:
            group["cargo_tons_in_transit"] = float(group["cargo_tons_in_transit"]) + craft.capacity_metrics.cargo_mass_used
        if craft.status in ROUTE_PLANNED_STATUSES:
            group["planned_craft_count"] = int(group["planned_craft_count"]) + 1
            if craft.departure and (not group["next_departure"] or craft.departure < group["next_departure"]):
                group["next_departure"] = craft.departure
        if craft.arrival and craft.status in ROUTE_LOAD_STATUSES:
            if not group["next_arrival"] or craft.arrival < group["next_arrival"]:
                group["next_arrival"] = craft.arrival
        group["companies"].add(craft.company)
        group["assigned_craft"].append(f"{craft.craft_name} ({craft.company})")
        group["status_counts"][craft.status] = int(group["status_counts"].get(craft.status, 0)) + 1
        if craft.cargo:
            group["cargo_summaries"].append(craft.cargo)
        if craft.fuel_plan:
            group["fuel_plan_summaries"].append(f"{craft.craft_name}: {craft.fuel_plan}")
        if craft.capacity:
            group["capacity_summaries"].append(f"{craft.craft_name}: {craft.capacity}")
        if craft.transfer:
            group["transfers"].add(craft.transfer)
        if craft.warnings:
            group["warnings"].update(part.strip() for part in craft.warnings.split(";") if part.strip())

    for cargo in cargo_facts or []:
        if cargo.source_type != "mission" or cargo.mission_status not in ROUTE_LOAD_STATUSES:
            continue
        if cargo.cargo_kind not in {"human", "crew_module"} or not cargo.route:
            continue
        group = route_group(cargo.route, cargo.mission_type)
        group["people_in_transit"] = int(group["people_in_transit"]) + max(cargo.people, 0)

    metrics: list[RouteMetric] = []
    for route, group in grouped.items():
        status_counts = tuple(sorted((str(status), int(count)) for status, count in group["status_counts"].items()))
        warnings = tuple(sorted(group["warnings"]))
        metrics.append(
            RouteMetric(
                route_key=route,
                route=route,
                route_type=str(group["route_type"] or ""),
                total_craft_count=int(group["total_craft_count"]),
                active_craft_count=int(group["active_craft_count"]),
                planned_craft_count=int(group["planned_craft_count"]),
                cargo_tons_in_transit=float(group["cargo_tons_in_transit"]),
                people_in_transit=int(group["people_in_transit"]),
                next_departure=str(group["next_departure"] or ""),
                next_arrival=str(group["next_arrival"] or ""),
                attention_count=len(warnings),
                companies=tuple(sorted(group["companies"])),
                status_counts=status_counts,
                assigned_craft=tuple(group["assigned_craft"]),
                cargo_summaries=tuple(group["cargo_summaries"]),
                fuel_plan_summaries=tuple(group["fuel_plan_summaries"]),
                capacity_summaries=tuple(group["capacity_summaries"]),
                transfers=tuple(sorted(group["transfers"])),
                warnings=warnings,
            )
        )
    return sorted(metrics, key=lambda item: (item.next_arrival or "9999", item.route))
