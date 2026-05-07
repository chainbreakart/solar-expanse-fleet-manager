from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .fact_model import (
    CargoFact,
    CrewMetric,
    MissionFact,
    ObjectFact,
    PopulationDestinationMetric,
    PopulationFlightMetric,
    PopulationPlaceMetric,
    PopulationReadinessMetric,
    ResourceStockFact,
    TechReferenceCatalog,
    TechUnlockFact,
)
from .normalizer_utils import as_float, fmt_num, fmt_rate, game_key, id_value, list_content
from .technology_adjustments import life_support_consumption_adjustment, unlocked_reference_modifiers

STATUS_RANK = {"Safe": 0, "Monitor": 1, "Warning": 2, "Urgent": 3, "Critical": 4}
CREW_METRIC_STATUSES = {"En route", "Cyclical", "Planned", "Cyclical paused"}
SUPPLY_RESOURCE_KEY = "id_resource_supply"
HUMAN_RESOURCE_KEY = "id_resource_human"
SURFACE_LIFE_SUPPORT_MULTIPLIER = 5.0
CREW_IN_HABITATS_LIFE_SUPPORT_MULTIPLIER = 0.5
SUPPLY_TO_LIFE_SUPPORT_MULTIPLIER = 365.0


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


def load_habitat_capacity_map(repo_root: Path) -> dict[str, float]:
    capacities: dict[str, float] = {}
    path = repo_root / "data" / "derived" / "population" / "habitat_capacities.csv"
    if not path.exists():
        return capacities
    import csv

    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("context") == "Transport":
                continue
            key = row.get("game_key") or ""
            try:
                capacity = float(row.get("capacity_per_unit") or 0.0)
            except ValueError:
                capacity = 0.0
            if key and capacity and capacity > 0:
                capacities[key] = capacity
    return capacities


def object_company_rows(save: dict[str, Any], included_companies: set[str] | None = None) -> dict[tuple[str, int], dict[str, Any]]:
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in list_content(save.get("objectInfoDatas")):
        if not isinstance(row, dict):
            continue
        company = str(id_value(row.get("companyId"), ""))
        object_id = row.get("id") if isinstance(row.get("id"), int) else None
        if not company or object_id is None:
            continue
        if included_companies is not None and company not in included_companies:
            continue
        rows[(company, object_id)] = row
    return rows


def facility_descriptor_key(item: dict[str, Any]) -> str:
    return game_key(item.get("facilityDescriptor") or item.get("productionItemType") or item.get("idProductionItemType"))


def facility_quantity(item: dict[str, Any]) -> float:
    for key in ("enabled", "quantity"):
        value = as_float(item.get(key))
        if value and value > 0:
            return value
    return 1.0


def housing_capacity_from_items(
    items: list[Any],
    habitat_capacities: dict[str, float],
) -> tuple[float, float]:
    completed = 0.0
    queued = 0.0
    seen: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if isinstance(item_id, int):
            if item_id in seen:
                continue
            seen.add(item_id)
        capacity_per_unit = habitat_capacities.get(facility_descriptor_key(item))
        if not capacity_per_unit:
            continue
        multiplier = as_float(item.get("singlePowerProductionMultiplier")) or 1.0
        capacity = capacity_per_unit * facility_quantity(item) * multiplier
        build_progress = as_float(item.get("buildProgress"))
        if build_progress is not None and build_progress < 1.0:
            queued += capacity
        else:
            completed += capacity
    return completed, queued


def housing_capacity_for_row(row: dict[str, Any] | None, habitat_capacities: dict[str, float]) -> tuple[float, float]:
    if not isinstance(row, dict):
        return 0.0, 0.0
    items = list_content(row.get("listFacility")) + list_content(row.get("productionItems"))
    return housing_capacity_from_items(items, habitat_capacities)


def explicit_cargo_quantity(raw: dict[str, Any]) -> float:
    for key in ("quantity", "count"):
        quantity = as_float(raw.get(key))
        if quantity and quantity > 0:
            return quantity
    return 1.0


def arriving_habitat_capacity(cargo: CargoFact, habitat_capacities: dict[str, float]) -> float:
    capacity = habitat_capacities.get(cargo.module_key) or habitat_capacities.get(cargo.resource_key)
    if not capacity:
        return 0.0
    return capacity * explicit_cargo_quantity(cargo.raw)


def stock_fact_lookup(resource_stock_facts: list[ResourceStockFact]) -> dict[tuple[str, int, str], ResourceStockFact]:
    lookup: dict[tuple[str, int, str], ResourceStockFact] = {}
    for stock in resource_stock_facts:
        lookup[(stock.company, stock.object_id, stock.resource_key)] = stock
    return lookup


def modeled_surface_supply_demand(population: float, housing_capacity: float) -> float:
    population = max(population, 0.0)
    unhoused = max(population - max(housing_capacity, 0.0), 0.0)
    life_support = (
        population * CREW_IN_HABITATS_LIFE_SUPPORT_MULTIPLIER
        + unhoused
    ) / SURFACE_LIFE_SUPPORT_MULTIPLIER
    return life_support / SUPPLY_TO_LIFE_SUPPORT_MULTIPLIER


def effective_supply_modifier(saved_outtake: float, base_modeled_demand: float) -> tuple[float, str]:
    if saved_outtake > 0 and base_modeled_demand > 0:
        modifier = max(saved_outtake / base_modeled_demand, 0.0)
        return modifier, "derived from saved Supply outTake / base modeled current population demand"
    return 1.0, "default 1.0; no current saved population burn to derive local modifier"


def population_severity_rank(severity: str) -> int:
    return {"Safe": 0, "Monitor": 1, "Warning": 2, "Urgent": 3, "Critical": 4}.get(severity, 0)


def stronger_population_severity(left: str, right: str) -> str:
    return left if population_severity_rank(left) >= population_severity_rank(right) else right


def supply_runway_severity(runway_days: float | None, projected_net: float) -> str:
    if projected_net >= 0 or runway_days is None:
        return "Safe"
    if runway_days < 365.0 / 2.0:
        return "Critical"
    if runway_days < 365.0:
        return "Urgent"
    if runway_days < 365.0 * 2.0:
        return "Warning"
    return "Monitor"


def build_population_readiness_details(
    *,
    destination: str,
    inbound_people: int,
    current_population: float,
    projected_population: float,
    completed_housing: float,
    queued_housing: float,
    arriving_housing: float,
    housing_gap: float,
    supply_stock: float,
    supply_intake: float,
    supply_outtake: float,
    effective_modifier: float,
    modifier_basis: str,
    added_supply_demand: float,
    projected_outtake: float,
    projected_net: float,
    runway_days: float | None,
) -> tuple[str, ...]:
    return (
        f"Destination: {destination}",
        f"People: {fmt_num(current_population)} current + {inbound_people} inbound = {fmt_num(projected_population)} projected",
        f"Housing: {fmt_num(completed_housing)} ready + {fmt_num(queued_housing)} queued + {fmt_num(arriving_housing)} arriving; gap {fmt_num(housing_gap)}",
        f"Supply stock: {fmt_num(supply_stock)}t",
        f"Supply flow: +{fmt_rate(supply_intake)}t/day production, -{fmt_rate(supply_outtake)}t/day current use",
        f"Local Supply modifier: {fmt_rate(effective_modifier)}x ({modifier_basis})",
        f"Inbound population demand estimate: -{fmt_rate(added_supply_demand)}t/day",
        f"Projected net supply: {fmt_rate(projected_net)}t/day; runway {runway_label(runway_days, projected_net)}",
        "Runway uses current save stock/intake/outtake plus local-modified marginal housed/unhoused population consumption.",
    )


def build_population_readiness_metrics(
    save: dict[str, Any],
    repo_root: Path,
    cargo_facts: list[CargoFact],
    mission_facts: list[MissionFact],
    resource_stock_facts: list[ResourceStockFact],
    object_facts: dict[int, ObjectFact],
    included_companies: set[str] | None = None,
    technology_reference: TechReferenceCatalog | None = None,
    tech_unlock_facts: list[TechUnlockFact] | None = None,
) -> list[PopulationReadinessMetric]:
    habitat_capacities = load_habitat_capacity_map(repo_root)
    object_rows = object_company_rows(save, included_companies)
    stocks = stock_fact_lookup(resource_stock_facts)
    mission_by_key = {mission.mission_key: mission for mission in mission_facts}

    people_by_mission: dict[str, int] = {}
    people_by_destination: dict[tuple[str, int], int] = {}
    for cargo in cargo_facts:
        if cargo.source_type != "mission" or cargo.mission_status not in CREW_METRIC_STATUSES:
            continue
        if cargo.cargo_kind not in {"human", "crew_module"} or cargo.people <= 0:
            continue
        mission = mission_by_key.get(cargo.mission_key)
        if not mission or mission.target_id is None:
            continue
        people_by_mission[cargo.mission_key] = people_by_mission.get(cargo.mission_key, 0) + cargo.people
        key = (cargo.company, mission.target_id)
        people_by_destination[key] = people_by_destination.get(key, 0) + cargo.people

    metrics: list[PopulationReadinessMetric] = []
    for mission_key, mission_people in sorted(people_by_mission.items()):
        mission = mission_by_key.get(mission_key)
        if not mission or mission.target_id is None:
            continue
        destination_id = mission.target_id
        destination = object_facts.get(destination_id).label if destination_id in object_facts else object_label(object_facts, destination_id)
        inbound_people = people_by_destination.get((mission.company, destination_id), mission_people)
        object_row = object_rows.get((mission.company, destination_id))
        completed_housing, queued_housing = housing_capacity_for_row(object_row, habitat_capacities)
        arriving_housing = 0.0
        for cargo in cargo_facts:
            if cargo.source_type != "mission" or cargo.mission_status not in CREW_METRIC_STATUSES:
                continue
            cargo_mission = mission_by_key.get(cargo.mission_key)
            if not cargo_mission or cargo_mission.company != mission.company or cargo_mission.target_id != destination_id:
                continue
            if cargo.arrival_dt and mission.arrival_dt and cargo.arrival_dt > mission.arrival_dt:
                continue
            arriving_housing += arriving_habitat_capacity(cargo, habitat_capacities)

        human_stock = stocks.get((mission.company, destination_id, HUMAN_RESOURCE_KEY))
        supply_stock = stocks.get((mission.company, destination_id, SUPPLY_RESOURCE_KEY))
        current_population = human_stock.value if human_stock else 0.0
        projected_population = current_population + inbound_people
        projected_housing = completed_housing + queued_housing + arriving_housing
        housing_gap = max(projected_population - projected_housing, 0.0)

        supply_value = supply_stock.value if supply_stock else 0.0
        supply_intake = supply_stock.intake if supply_stock else 0.0
        supply_outtake = supply_stock.outtake if supply_stock else 0.0
        current_modeled_supply = modeled_surface_supply_demand(current_population, completed_housing)
        projected_modeled_supply = modeled_surface_supply_demand(projected_population, projected_housing)
        supply_modifier, supply_modifier_basis = effective_supply_modifier(supply_outtake, current_modeled_supply)
        raw_added_supply_demand = max(projected_modeled_supply - current_modeled_supply, 0.0) * supply_modifier
        unlocked_modifiers = unlocked_reference_modifiers(technology_reference, tech_unlock_facts, mission.company)
        added_supply_demand, supply_tech_adjustment = life_support_consumption_adjustment(
            unlocked_modifiers,
            raw_demand=raw_added_supply_demand,
            apply_to_saved_outtake=supply_modifier_basis.startswith("derived from saved"),
        )
        if supply_tech_adjustment:
            supply_modifier_basis = f"{supply_modifier_basis}; tech {supply_tech_adjustment.basis}"
        projected_outtake = supply_outtake + added_supply_demand
        projected_net = supply_intake - projected_outtake
        runway_days = supply_value / abs(projected_net) if projected_net < 0 else None

        severity = supply_runway_severity(runway_days, projected_net)
        messages: list[str] = []
        if severity != "Safe":
            messages.append(f"supply runway {runway_label(runway_days, projected_net)}")
        if housing_gap > 0:
            housing_severity = "Critical" if completed_housing + queued_housing <= 0 else "Urgent"
            severity = stronger_population_severity(severity, housing_severity)
            messages.append(f"housing short {fmt_num(housing_gap)}")
        elif projected_population > completed_housing and queued_housing > 0:
            severity = stronger_population_severity(severity, "Warning")
            messages.append("housing depends on build queue")

        status = severity
        if status == "Safe":
            message = "Safe: housing and supply runway look adequate"
        else:
            message = f"{status}: " + "; ".join(messages)

        metrics.append(
            PopulationReadinessMetric(
                readiness_key=mission_key,
                company=mission.company,
                mission_key=mission_key,
                destination_id=destination_id,
                destination=destination,
                inbound_people=inbound_people,
                current_population=current_population,
                projected_population=projected_population,
                completed_housing=completed_housing,
                queued_housing=queued_housing,
                arriving_housing=arriving_housing,
                housing_gap=housing_gap,
                supply_stock=supply_value,
                supply_intake_per_day=supply_intake,
                supply_outtake_per_day=supply_outtake,
                effective_supply_modifier=supply_modifier,
                supply_modifier_basis=supply_modifier_basis,
                added_supply_demand_per_day=added_supply_demand,
                raw_added_supply_demand_per_day=raw_added_supply_demand,
                projected_supply_outtake_per_day=projected_outtake,
                projected_supply_net_per_day=projected_net,
                supply_runway_days=runway_days,
                severity=severity,
                status=status,
                message=message,
                details=build_population_readiness_details(
                    destination=destination,
                    inbound_people=inbound_people,
                    current_population=current_population,
                    projected_population=projected_population,
                    completed_housing=completed_housing,
                    queued_housing=queued_housing,
                    arriving_housing=arriving_housing,
                    housing_gap=housing_gap,
                    supply_stock=supply_value,
                    supply_intake=supply_intake,
                    supply_outtake=supply_outtake,
                    effective_modifier=supply_modifier,
                    modifier_basis=supply_modifier_basis,
                    added_supply_demand=added_supply_demand,
                    projected_outtake=projected_outtake,
                    projected_net=projected_net,
                    runway_days=runway_days,
                ),
                tech_adjustment=supply_tech_adjustment,
            )
        )

    return metrics


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
