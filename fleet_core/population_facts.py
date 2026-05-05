from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .fact_model import (
    CrewMetric,
    MissionFact,
    ObjectFact,
    PopulationDestinationMetric,
    PopulationFlightMetric,
    PopulationPlaceMetric,
    PopulationReadinessMetric,
    ResourceStockFact,
)
from .normalizer import (
    HUMAN_RESOURCE_KEY,
    SUPPLY_RESOURCE_KEY,
    effective_supply_modifier,
    fmt_num,
    fmt_rate,
    housing_capacity_for_row,
    load_habitat_capacity_map,
    modeled_surface_supply_demand,
    object_company_rows,
    stock_fact_lookup,
    supply_runway_severity,
)

STATUS_RANK = {"Safe": 0, "Monitor": 1, "Warning": 2, "Urgent": 3, "Critical": 4}


def runway_label(days: float | None, projected_net: float) -> str:
    if projected_net >= 0 or days is None:
        return "stable"
    if days >= 365:
        return f"{fmt_num(days / 365)}y"
    return f"{fmt_num(days)}d"


def worst_status(statuses: list[str]) -> str:
    return max(statuses or ["Unknown"], key=lambda status: STATUS_RANK.get(status, -1))


def sort_dt_key(value: datetime | None) -> datetime:
    return value if value else datetime.max


def object_label(object_facts: dict[int, ObjectFact], object_id: int | None) -> str:
    if object_id is None:
        return ""
    fact = object_facts.get(object_id)
    return fact.label if fact else f"Object {object_id}"


def population_destination_details(metric: PopulationReadinessMetric) -> tuple[str, ...]:
    return metric.details


def build_population_destination_metrics(
    population_readiness_metrics: list[PopulationReadinessMetric],
    mission_facts: list[MissionFact],
    object_facts: dict[int, ObjectFact],
) -> list[PopulationDestinationMetric]:
    missions = {mission.mission_key: mission for mission in mission_facts}
    groups: dict[tuple[str, int | None], list[PopulationReadinessMetric]] = defaultdict(list)
    for metric in population_readiness_metrics:
        groups[(metric.company, metric.destination_id)].append(metric)

    rows: list[PopulationDestinationMetric] = []
    for (company, destination_id), metrics in groups.items():
        arrivals = [
            mission.arrival_dt
            for metric in metrics
            if (mission := missions.get(metric.mission_key)) is not None
        ]
        next_arrival_dt = min((arrival for arrival in arrivals if arrival is not None), default=None)
        status = worst_status([metric.status for metric in metrics])
        worst_metric = max(metrics, key=lambda metric: STATUS_RANK.get(metric.status, -1))
        finite_runways = [
            metric.supply_runway_days
            for metric in metrics
            if metric.supply_runway_days is not None and metric.projected_supply_net_per_day < 0
        ]
        runway_days = min(finite_runways) if finite_runways else None
        projected_net = min((metric.projected_supply_net_per_day for metric in metrics), default=0.0)

        rows.append(
            PopulationDestinationMetric(
                destination_key=f"{company}:{destination_id}",
                company=company,
                destination_id=destination_id,
                destination=object_label(object_facts, destination_id) or worst_metric.destination,
                status=status,
                message=worst_metric.message,
                details=population_destination_details(worst_metric),
                inbound_people=max((metric.inbound_people for metric in metrics), default=0),
                current_population=max((metric.current_population for metric in metrics), default=0.0),
                projected_population=max((metric.projected_population for metric in metrics), default=0.0),
                completed_housing=max((metric.completed_housing for metric in metrics), default=0.0),
                queued_housing=max((metric.queued_housing for metric in metrics), default=0.0),
                arriving_housing=max((metric.arriving_housing for metric in metrics), default=0.0),
                housing_gap=max((metric.housing_gap for metric in metrics), default=0.0),
                supply_stock=max((metric.supply_stock for metric in metrics), default=0.0),
                supply_intake_per_day=max((metric.supply_intake_per_day for metric in metrics), default=0.0),
                projected_supply_outtake_per_day=max(
                    (metric.projected_supply_outtake_per_day for metric in metrics),
                    default=0.0,
                ),
                projected_supply_net_per_day=projected_net,
                supply_runway_days=runway_days,
                next_arrival=next_arrival_dt.strftime("%Y-%m-%d") if next_arrival_dt else "",
                next_arrival_dt=next_arrival_dt,
            )
        )
    return sorted(rows, key=lambda row: (STATUS_RANK.get(row.status, -1) * -1, sort_dt_key(row.next_arrival_dt)))


def build_population_flight_metrics(
    crew_metrics: list[CrewMetric],
    mission_facts: list[MissionFact],
    population_readiness_metrics: list[PopulationReadinessMetric],
    object_facts: dict[int, ObjectFact],
) -> list[PopulationFlightMetric]:
    missions = {mission.mission_key: mission for mission in mission_facts}
    readiness_by_mission = {
        metric.mission_key: metric for metric in population_readiness_metrics
    }
    grouped: dict[str, dict[str, Any]] = {}
    for metric in crew_metrics:
        group = grouped.setdefault(
            metric.mission_key,
            {
                "mission_key": metric.mission_key,
                "mission_id": metric.mission_id,
                "company": metric.company,
                "status": metric.status,
                "craft": set(),
                "people": 0,
                "empty_seats": 0,
                "loaded_modules": 0,
                "empty_modules": 0,
                "life_support": metric.life_support_carriage,
            },
        )
        if metric.craft_name:
            group["craft"].add(metric.craft_name)
        group["people"] += metric.people
        group["empty_seats"] += metric.empty_seats or 0
        if metric.state == "Loaded":
            group["loaded_modules"] += 1
        if metric.state == "Empty":
            group["empty_modules"] += 1
        if not group["life_support"] and metric.life_support_carriage:
            group["life_support"] = metric.life_support_carriage

    rows: list[PopulationFlightMetric] = []
    for mission_key, group in grouped.items():
        mission = missions.get(mission_key)
        if mission is None:
            continue
        readiness = readiness_by_mission.get(mission_key)
        rows.append(
            PopulationFlightMetric(
                flight_key=mission_key,
                mission_key=mission_key,
                mission_id=str(group["mission_id"]),
                company=str(group["company"]),
                status=str(group["status"]),
                craft_names=tuple(sorted(group["craft"])),
                people=int(group["people"]),
                empty_seats=int(group["empty_seats"]),
                loaded_modules=int(group["loaded_modules"]),
                empty_modules=int(group["empty_modules"]),
                life_support=float(group["life_support"]),
                route=mission.route,
                source=object_label(object_facts, mission.start_id),
                destination=object_label(object_facts, mission.target_id),
                departure=mission.departure,
                arrival=mission.arrival,
                departure_dt=mission.departure_dt,
                arrival_dt=mission.arrival_dt,
                duration_days=mission.timing.duration_days,
                readiness_status=readiness.status if readiness else ("Safe" if int(group["people"]) <= 0 else "Unknown"),
                readiness_message=readiness.message if readiness else "",
                readiness_details=readiness.details if readiness else (),
            )
        )
    return sorted(rows, key=lambda row: (sort_dt_key(row.arrival_dt), row.company, row.mission_id))


def place_status(housing_gap: float, runway_days: float | None, supply_net: float) -> str:
    status = supply_runway_severity(runway_days, supply_net)
    if housing_gap > 0:
        status = worst_status([status, "Urgent"])
    return status


def build_population_place_metrics(
    save: dict[str, Any],
    repo_root: Path,
    included_companies: set[str] | None,
    resource_stock_facts: list[ResourceStockFact],
    population_readiness_metrics: list[PopulationReadinessMetric],
    object_facts: dict[int, ObjectFact],
) -> list[PopulationPlaceMetric]:
    habitat_capacities = load_habitat_capacity_map(repo_root)
    object_rows = object_company_rows(save, included_companies)
    stocks = stock_fact_lookup(resource_stock_facts)
    inbound_people: dict[tuple[str, int], int] = defaultdict(int)
    for metric in population_readiness_metrics:
        if metric.destination_id is not None:
            key = (metric.company, metric.destination_id)
            inbound_people[key] = max(inbound_people[key], metric.inbound_people)

    row_keys = set(object_rows)
    row_keys.update((stock.company, stock.object_id) for stock in resource_stock_facts if stock.resource_key == HUMAN_RESOURCE_KEY)
    row_keys.update(inbound_people)

    rows: list[PopulationPlaceMetric] = []
    for company, object_id in sorted(row_keys, key=lambda item: (item[0], item[1])):
        object_fact = object_facts.get(object_id)
        object_row = object_rows.get((company, object_id))
        human_stock = stocks.get((company, object_id, HUMAN_RESOURCE_KEY))
        supply_stock = stocks.get((company, object_id, SUPPLY_RESOURCE_KEY))
        current_population = human_stock.value if human_stock else 0.0
        completed_housing, queued_housing = housing_capacity_for_row(object_row, habitat_capacities)
        incoming = inbound_people.get((company, object_id), 0)
        if current_population <= 0 and completed_housing <= 0 and queued_housing <= 0 and incoming <= 0:
            continue

        modeled_demand = modeled_surface_supply_demand(current_population, completed_housing)
        saved_outtake = supply_stock.outtake if supply_stock else 0.0
        modifier, modifier_basis = effective_supply_modifier(saved_outtake, modeled_demand)
        estimated_outtake = saved_outtake or modeled_demand * modifier
        supply_value = supply_stock.value if supply_stock else 0.0
        supply_intake = supply_stock.intake if supply_stock else 0.0
        supply_net = supply_intake - estimated_outtake
        runway_days = supply_value / abs(supply_net) if supply_net < 0 else None
        housing_gap = max(current_population - completed_housing, 0.0)
        free_housing = max(completed_housing - current_population, 0.0)
        status = place_status(housing_gap, runway_days, supply_net)
        pieces = []
        if housing_gap > 0:
            pieces.append(f"housing short {fmt_num(housing_gap)}")
        if supply_net < 0:
            pieces.append(f"Supply runway {runway_label(runway_days, supply_net)}")
        if incoming:
            pieces.append(f"{incoming} people inbound")
        if status == "Monitor" and pieces:
            message = "Monitor: long-range drawdown; " + "; ".join(pieces)
        else:
            message = f"{status}: " + "; ".join(pieces) if pieces else "Safe: current population support looks stable"
        details = (
            f"Population: {fmt_num(current_population)}",
            f"Ready housing: {fmt_num(completed_housing)}",
            f"Queued housing: {fmt_num(queued_housing)}",
            f"Free housing now: {fmt_num(free_housing)}",
            f"Inbound people: {incoming}",
            f"Supply stock: {fmt_num(supply_value)}t",
            f"Supply intake/day: {fmt_rate(supply_intake)}",
            f"Estimated Supply out/day: {fmt_rate(estimated_outtake)}",
            f"Net Supply/day: {fmt_rate(supply_net)}",
            f"Runway: {runway_label(runway_days, supply_net)}",
            f"Supply modifier: {fmt_rate(modifier)} ({modifier_basis})",
        )

        rows.append(
            PopulationPlaceMetric(
                place_key=f"{company}:{object_id}",
                company=company,
                object_id=object_id,
                place=object_fact.label if object_fact else f"Object {object_id}",
                object_type=object_fact.object_type if object_fact else "",
                relationship=object_fact.relationship if object_fact else "",
                status=status,
                message=message,
                details=details,
                current_population=current_population,
                completed_housing=completed_housing,
                queued_housing=queued_housing,
                free_housing=free_housing,
                housing_gap=housing_gap,
                supply_stock=supply_value,
                supply_intake_per_day=supply_intake,
                supply_outtake_per_day=estimated_outtake,
                supply_net_per_day=supply_net,
                supply_modifier=modifier,
                supply_modifier_basis=modifier_basis,
                supply_runway_days=runway_days,
                inbound_people=incoming,
            )
        )
    return sorted(
        rows,
        key=lambda row: (STATUS_RANK.get(row.status, -1) * -1, -row.current_population, row.place),
    )
