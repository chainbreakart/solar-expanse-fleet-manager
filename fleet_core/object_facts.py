from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .fact_model import MissionFact, ObjectFact
from .normalizer_utils import as_bool, as_float, as_int, extract_datetime, id_value, list_content


def load_object_reference(repo_root: Path) -> dict[int, dict[str, str]]:
    reference: dict[int, dict[str, str]] = {}
    reference_paths = (
        repo_root / "products" / "apps" / "fleet_manager" / "data" / "object_id_reference.csv",
        repo_root / "data" / "object_id_reference.csv",
    )
    reference_path = next((path for path in reference_paths if path.exists()), reference_paths[0])
    if not reference_path.exists():
        return reference

    with reference_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            object_id = as_int(row.get("object_id"))
            if object_id is None:
                continue
            reference[object_id] = row
    return reference


def build_object_metadata(save: dict[str, Any], repo_root: Path) -> tuple[dict[int, str], dict[int, str]]:
    names: dict[int, str] = {
        59: "Mars",
        66: "Earth",
    }
    types: dict[int, str] = {
        59: "Planet",
        66: "Planet",
    }
    for object_id, row in load_object_reference(repo_root).items():
        display_name = row.get("display_name")
        if display_name:
            names[object_id] = display_name
        object_type = row.get("object_type_name")
        if object_type:
            types[object_id] = object_type

    carbon_path = repo_root / "inspect" / "economy_equilibrium" / "outputs" / "solar_system_carbon_stock_by_object.csv"
    if carbon_path.exists():
        with carbon_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                try:
                    object_id = int(row["object_id"])
                except (KeyError, TypeError, ValueError):
                    pass
                else:
                    if object_id not in names:
                        names[object_id] = row.get("object_name") or row.get("display_name") or f"Object {object_id}"
                    if object_id not in types and row.get("object_type"):
                        types[object_id] = row["object_type"]

    for obj in list_content(save.get("ObjectInfoSaves")):
        object_id = object_info_id(obj.get("IDObjectInfo")) if isinstance(obj, dict) else None
        custom_name = obj.get("customName") if isinstance(obj, dict) else None
        if isinstance(object_id, int) and custom_name:
            names[object_id] = custom_name

    return names, types


def object_relationship(object_type: str) -> tuple[str, bool, bool]:
    if object_type == "Orbit":
        return "Orbit", True, False
    if object_type == "SolarOrbit":
        return "Solar orbit", True, False
    if object_type in {"Planet", "Moon", "Asteroid", "Comet"}:
        return "Surface", False, True
    return object_type or "Unknown", False, False


def company_id_from_object_data(row: dict[str, Any]) -> str:
    return str(id_value(row.get("companyId"), ""))


def object_data_has_activity(row: dict[str, Any]) -> bool:
    for key in ("constructionEquipmentCount", "crewValueInWork", "resourcesExplorationPower"):
        value = as_float(row.get(key))
        if value and abs(value) > 0.0001:
            return True
    for key in ("productionItems", "listFacility", "listSpacecraftConstruct"):
        if list_content(row.get(key)):
            return True
    for resource in list_content(row.get("listRowResourcesData")):
        if not isinstance(resource, dict):
            continue
        for key in ("value", "inTake", "outTake", "valueBeforeChange"):
            value = as_float(resource.get(key))
            if value and abs(value) > 0.0001:
                return True
    return False


def object_info_id(value: Any) -> int | None:
    raw = id_value(value) if isinstance(value, dict) else value
    return as_int(raw)


def object_label(object_id: Any, names: dict[int, str]) -> str:
    if not isinstance(object_id, int) or object_id < 0:
        return "-"
    name = names.get(object_id)
    return f"{name} ({object_id})" if name else f"Object {object_id}"


def build_object_names(save: dict[str, Any], repo_root: Path) -> dict[int, str]:
    names, _ = build_object_metadata(save, repo_root)
    return names


def build_object_facts(
    save: dict[str, Any],
    repo_root: Path,
    mission_facts: list[MissionFact] | None = None,
    included_companies: set[str] | None = None,
) -> dict[int, ObjectFact]:
    object_names, object_types = build_object_metadata(save, repo_root)
    reference = load_object_reference(repo_root)
    companies = [company for company in list_content(save.get("companyDataSave")) if isinstance(company, dict)]
    if mission_facts is None:
        mission_facts = []
    _current_time = extract_datetime(save.get("currentTime"))

    object_ids: set[int] = set(reference)
    raw_objects: dict[int, dict[str, Any]] = {}
    owner_companies: dict[int, set[str]] = {}
    present_craft: dict[int, int] = {}
    inbound_missions: dict[int, int] = {}
    outbound_missions: dict[int, int] = {}
    next_arrivals: dict[int, str] = {}

    def include_company(company_id: str) -> bool:
        return included_companies is None or company_id in included_companies

    def add_owner(object_id: int | None, company_id: str) -> None:
        if object_id is None or not company_id or not include_company(company_id):
            return
        owner_companies.setdefault(object_id, set()).add(company_id)

    for obj in list_content(save.get("ObjectInfoSaves")):
        if not isinstance(obj, dict):
            continue
        object_id = object_info_id(obj.get("IDObjectInfo"))
        if isinstance(object_id, int):
            object_ids.add(object_id)
            raw_objects[object_id] = obj

    for row in list_content(save.get("objectInfoDatas")):
        if not isinstance(row, dict):
            continue
        object_id = row.get("id")
        company_id = company_id_from_object_data(row)
        if not isinstance(object_id, int) or not include_company(company_id):
            continue
        object_ids.add(object_id)
        if object_data_has_activity(row):
            add_owner(object_id, company_id)

    for company in companies:
        company_id = str(id_value(company.get("companyID"), ""))
        if not include_company(company_id):
            continue
        for craft in list_content(company.get("spacecrafts")):
            if not isinstance(craft, dict):
                continue
            object_id = craft.get("idObjectInfo")
            if not isinstance(object_id, int):
                continue
            object_ids.add(object_id)
            present_craft[object_id] = present_craft.get(object_id, 0) + 1
            add_owner(object_id, company_id)

    active_statuses = {"Planned", "En route", "Cyclical", "Cyclical paused"}
    for mission in mission_facts:
        if not include_company(mission.company):
            continue
        for object_id in (mission.start_id, mission.target_id):
            if isinstance(object_id, int):
                object_ids.add(object_id)
        if mission.status not in active_statuses:
            continue
        for object_id in (mission.start_id, mission.target_id):
            if isinstance(object_id, int):
                add_owner(object_id, mission.company)
        if mission.route_type == "cyclical":
            for object_id in (mission.start_id, mission.target_id):
                if not isinstance(object_id, int):
                    continue
                inbound_missions[object_id] = inbound_missions.get(object_id, 0) + 1
                outbound_missions[object_id] = outbound_missions.get(object_id, 0) + 1
        else:
            if isinstance(mission.start_id, int):
                outbound_missions[mission.start_id] = outbound_missions.get(mission.start_id, 0) + 1
            if isinstance(mission.target_id, int):
                inbound_missions[mission.target_id] = inbound_missions.get(mission.target_id, 0) + 1
                if mission.arrival and (not next_arrivals.get(mission.target_id) or mission.arrival < next_arrivals[mission.target_id]):
                    next_arrivals[mission.target_id] = mission.arrival

    facts: dict[int, ObjectFact] = {}
    for object_id in sorted(object_ids):
        row = reference.get(object_id, {})
        display_name = object_names.get(object_id) or row.get("display_name") or f"Object {object_id}"
        object_type = object_types.get(object_id) or row.get("object_type_name") or ""
        object_type_id = as_int(row.get("object_type"))
        parent_id = as_int(row.get("parent_id"))
        parent_name = object_names.get(parent_id, "") if parent_id is not None else ""
        relationship, is_orbit, is_surface = object_relationship(object_type)
        facts[object_id] = ObjectFact(
            object_id=object_id,
            display_name=display_name,
            label=object_label(object_id, object_names),
            object_type=object_type or "Unknown",
            object_type_id=object_type_id,
            parent_id=parent_id,
            parent_name=parent_name,
            parent_label=object_label(parent_id, object_names) if parent_id is not None else "",
            relationship=relationship,
            is_orbit=is_orbit,
            is_surface=is_surface,
            can_mine=as_bool(row.get("can_mine")),
            path_id=as_int(row.get("path_id")),
            owner_companies=tuple(sorted(owner_companies.get(object_id, set()))),
            present_craft=present_craft.get(object_id, 0),
            inbound_missions=inbound_missions.get(object_id, 0),
            outbound_missions=outbound_missions.get(object_id, 0),
            next_arrival=next_arrivals.get(object_id, ""),
            raw=raw_objects.get(object_id),
        )
    return facts
