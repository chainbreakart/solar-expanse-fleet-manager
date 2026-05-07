from __future__ import annotations

from datetime import datetime
from typing import Any

from .cargo_facts import cargo_mass, cargo_summary, fuel_mass, fuel_resource_key
from .fact_model import MissionFact, TimingMetrics
from .normalizer_utils import as_float, enum_name, extract_datetime, fmt_dt, id_value, list_content
from .object_facts import object_label


def build_timing_metrics(departure: datetime | None, arrival: datetime | None, current_time: datetime | None) -> TimingMetrics:
    if not departure or not arrival:
        return TimingMetrics(
            duration_days=None,
            percent_complete=None,
            days_until_departure=None,
            days_until_arrival=None,
            days_since_stale_arrival=None,
        )
    duration_days = max((arrival - departure).total_seconds() / 86400.0, 0.0)
    percent_complete: float | None = None
    days_until_departure: float | None = None
    days_until_arrival: float | None = None
    days_since_stale_arrival: float | None = None
    if current_time:
        if current_time < departure:
            days_until_departure = (departure - current_time).total_seconds() / 86400.0
            days_until_arrival = (arrival - current_time).total_seconds() / 86400.0
            percent_complete = 0.0 if duration_days > 0 else None
        elif current_time <= arrival:
            days_until_departure = 0.0
            days_until_arrival = (arrival - current_time).total_seconds() / 86400.0
            percent_complete = ((current_time - departure).total_seconds() / 86400.0) / duration_days * 100.0 if duration_days > 0 else None
        else:
            days_until_departure = 0.0
            days_until_arrival = 0.0
            days_since_stale_arrival = (current_time - arrival).total_seconds() / 86400.0
            percent_complete = 100.0 if duration_days > 0 else None
    return TimingMetrics(
        duration_days=duration_days,
        percent_complete=percent_complete,
        days_until_departure=days_until_departure,
        days_until_arrival=days_until_arrival,
        days_since_stale_arrival=days_since_stale_arrival,
    )


def timing_summary(departure: datetime | None, arrival: datetime | None, current_time: datetime | None) -> str:
    metrics = build_timing_metrics(departure, arrival, current_time)
    if metrics.duration_days is None:
        return ""
    duration_days = metrics.duration_days
    pieces = [f"{duration_days:.0f}d"]
    if current_time:
        if metrics.days_until_departure and metrics.days_until_departure > 0:
            pieces.append(f"starts in {metrics.days_until_departure:.0f}d")
        elif metrics.days_since_stale_arrival is not None:
            pieces.append(f"arrived {metrics.days_since_stale_arrival:.0f}d ago")
        elif metrics.percent_complete is not None and metrics.days_until_arrival is not None:
            pieces.append(f"{metrics.percent_complete:.0f}%")
            pieces.append(f"{metrics.days_until_arrival:.0f}d left")
    return "; ".join(pieces)


def mission_status(mission: dict[str, Any], current_time: datetime | None) -> str:
    if mission.get("cancel"):
        return "Canceled"
    departure = extract_datetime(mission.get("departureTimeDate"))
    arrival = extract_datetime(mission.get("arrival"))
    if current_time and departure and current_time < departure:
        return "Planned"
    if current_time and arrival and current_time > arrival:
        return "Arrived"
    return "En route"


def mission_craft_ids(mission: dict[str, Any], list_field: str = "sclistID") -> list[int]:
    craft_ids: list[int] = []
    sc_id = mission.get("scID")
    if isinstance(sc_id, int):
        craft_ids.append(sc_id)
    for craft_id in list_content(mission.get(list_field)):
        if isinstance(craft_id, int):
            craft_ids.append(craft_id)
    return list(dict.fromkeys(craft_ids))


def build_mission_facts(
    companies: list[dict[str, Any]],
    object_names: dict[int, str],
    resources: dict[str, str],
    buildables: dict[str, str],
    current_time: datetime | None,
) -> list[MissionFact]:
    facts: list[MissionFact] = []

    for company in companies:
        company_id = str(id_value(company.get("companyID"), ""))
        for mission in list_content(company.get("listMission")):
            if not isinstance(mission, dict):
                continue
            craft_ids = mission_craft_ids(mission)
            start_id = id_value(mission.get("start"))
            target_id = id_value(mission.get("target"))
            departure = extract_datetime(mission.get("departureTimeDate"))
            arrival = extract_datetime(mission.get("arrival"))
            cargo_all = mission.get("cargoAllData")
            mission_id = str(mission.get("missionID", ""))
            facts.append(
                MissionFact(
                    company=company_id,
                    mission_key=f"mission:{company_id}:{mission_id}",
                    mission_id=mission_id,
                    mission_type="mission",
                    raw=mission,
                    craft_ids=tuple(craft_id for craft_id in craft_ids if craft_id >= 0),
                    start_id=start_id if isinstance(start_id, int) else None,
                    target_id=target_id if isinstance(target_id, int) else None,
                    route=f"{object_label(start_id, object_names)} -> {object_label(target_id, object_names)}",
                    route_type="one-way",
                    status=mission_status(mission, current_time),
                    departure=fmt_dt(departure),
                    arrival=fmt_dt(arrival),
                    departure_dt=departure,
                    arrival_dt=arrival,
                    timing=build_timing_metrics(departure, arrival, current_time),
                    cargo=cargo_summary(cargo_all, resources, buildables),
                    fuel=fuel_summary(cargo_all, resources),
                    cargo_mass=cargo_mass(cargo_all),
                    fuel_mass=fuel_mass(cargo_all),
                    fuel_resource_key=fuel_resource_key(cargo_all),
                    planned_total_fuel=as_float(mission.get("allFuelNeed")),
                    optimal_fuel=as_float(mission.get("optimalFuelNeed")),
                    transfer=transfer_summary(mission, {}),
                )
            )

        for cycle_index, cycle in enumerate(list_content(company.get("listMissionCyclical"))):
            if not isinstance(cycle, dict):
                continue
            craft_ids = mission_craft_ids(cycle, "scIDList")
            start_id = cycle.get("A")
            target_id = cycle.get("B")
            status = "Cyclical paused" if cycle.get("Pause") else "Cyclical"
            ends = enum_name(cycle.get("Ends"), {0: "endless", 1: "count", 2: "until", 3: "resource target"})
            transfer = enum_name(cycle.get("TransferType"), {0: "optimal", 1: "fastest"})
            cargo_start = enum_name(cycle.get("CargoStart"), {0: "wait fill at A", 1: "fly available at A"})
            cargo_end = enum_name(cycle.get("CargoEnd"), {0: "wait fill at B", 1: "fly available at B"})
            details = "; ".join(part for part in [
                transfer,
                cargo_start,
                cargo_end,
                f"trips {cycle.get('CountMission')}/{cycle.get('CountMax')}" if cycle.get("CountMax") else f"trips {cycle.get('CountMission', 0)}",
                ends,
            ] if part)
            facts.append(
                MissionFact(
                    company=company_id,
                    mission_key=f"cycle:{company_id}:{cycle_index}",
                    mission_id="",
                    mission_type="cyclical",
                    raw=cycle,
                    craft_ids=tuple(craft_id for craft_id in craft_ids if craft_id >= 0),
                    start_id=start_id if isinstance(start_id, int) else None,
                    target_id=target_id if isinstance(target_id, int) else None,
                    route=f"{object_label(start_id, object_names)} <-> {object_label(target_id, object_names)}",
                    route_type="cyclical",
                    status=status,
                    departure="",
                    arrival="",
                    departure_dt=None,
                    arrival_dt=None,
                    timing=build_timing_metrics(None, None, current_time),
                    cargo="Cyclical route cargo",
                    fuel="",
                    cargo_mass=0.0,
                    fuel_mass=0.0,
                    fuel_resource_key="",
                    planned_total_fuel=None,
                    optimal_fuel=None,
                    transfer=details,
                )
            )

    return facts


def build_mission_index(mission_facts: list[MissionFact]) -> dict[tuple[str, int], MissionFact]:
    index: dict[tuple[str, int], MissionFact] = {}
    for fact in mission_facts:
        for craft_id in fact.craft_ids:
            key = (fact.company, craft_id)
            if fact.mission_type == "cyclical" and key in index:
                continue
            index[key] = fact
    return index


def fuel_summary(cargo_all: Any, resources: dict[str, str]) -> str:
    if not isinstance(cargo_all, dict):
        return ""
    fuel = cargo_all.get("cargoFuel")
    if not isinstance(fuel, dict):
        return ""
    from .normalizer_utils import fmt_num, friendly_key, game_key

    amount = fmt_num(fuel.get("cargoMass"))
    life_support = fmt_num(fuel.get("lifeSupportValue"))
    resource_key = game_key(fuel.get("resourceType"))
    name = resources.get(resource_key) or friendly_key(resource_key)
    pieces = []
    if amount:
        pieces.append(f"{name or 'Fuel'} {amount}t")
    if life_support:
        pieces.append(f"Life support {life_support}")
    return "; ".join(pieces)


def transfer_summary(mission: dict[str, Any], stats: dict[str, Any]) -> str:
    from .normalizer_utils import fmt_num

    pieces: list[str] = []
    if mission:
        pieces.append("constant/coast" if mission.get("noBurst") else "burst")
        if mission.get("cyclicalMission"):
            pieces.append("cyclical")
        delta_v = as_float(mission.get("deltaV"))
        if delta_v and abs(delta_v) > 0.05:
            pieces.append(f"dV {fmt_num(delta_v)}")
    propulsion = stats.get("propulsion_class") if stats else ""
    if propulsion:
        pieces.append(str(propulsion))
    if stats.get("continuous_burn_capable"):
        pieces.append("continuous")
    if stats.get("orbit_only"):
        pieces.append("orbit-only")
    elif stats.get("surface_capable"):
        pieces.append("surface-capable")
    return "; ".join(pieces)
