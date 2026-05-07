from __future__ import annotations

from pathlib import Path
from typing import Any

from .capacity_facts import (
    build_capacity_metrics,
    capacity_summary_for_semantics,
    fuel_plan_summary,
    movement_warnings,
)
from .cargo_facts import cargo_mass, cargo_summary, fuel_mass, fuel_resource_key, life_support_loaded
from .fact_model import CraftFact, MissionFact, TechReferenceCatalog, TechUnlockFact
from .mission_facts import (
    build_mission_facts,
    build_mission_index,
    build_timing_metrics,
    fuel_summary,
    timing_summary,
    transfer_summary,
)
from .normalizer_utils import (
    as_float,
    extract_datetime,
    friendly_key,
    game_key,
    id_value,
    list_content,
    normalized_name,
)
from .object_facts import build_object_metadata, object_label
from .spacecraft_reference import (
    CAPACITY_SEMANTICS_NORMAL,
    SPACECRAFT_TYPE_HULL_CANDIDATES,
    load_reference_maps,
    load_spacecraft_stats,
)
from .technology_adjustments import spacecraft_percent_capacity_adjustment, unlocked_reference_modifiers


def launchcraft_status(stats: dict[str, Any]) -> str:
    if stats.get("category") == "Launchcraft":
        return "Launchcraft"
    if stats.get("surface_capable"):
        return "Surface-capable"
    if stats.get("orbit_only"):
        return "Orbit-only"
    return ""


def build_craft_type_index(companies: list[dict[str, Any]]) -> dict[tuple[str, int], str]:
    index: dict[tuple[str, int], str] = {}
    for company in companies:
        company_id = str(id_value(company.get("companyID"), ""))
        for craft in list_content(company.get("spacecrafts")):
            if not isinstance(craft, dict):
                continue
            craft_id = craft.get("ID")
            if isinstance(craft_id, int):
                index[(company_id, craft_id)] = game_key(craft.get("spacecraftType"))
    return index


def build_company_hull_stats(companies: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float | None]]]:
    hulls_by_company: dict[str, dict[str, dict[str, float | None]]] = {}
    for company in companies:
        company_id = str(id_value(company.get("companyID"), ""))
        hulls: dict[str, dict[str, float | None]] = {}
        for hull in list_content(company.get("hullList")):
            if not isinstance(hull, dict) or not hull.get("isCompletedDesign"):
                continue
            hull_name = str(hull.get("hullName") or "")
            hull_base_name = str(hull.get("hullBaseName") or "")
            cargo_capacity = as_float(hull.get("cargoCapacityBase"))
            fuel_capacity = as_float(hull.get("fuelCapacityBase"))
            if not hull_name and not hull_base_name:
                continue
            stats = {
                "cargo_capacity_t": cargo_capacity,
                "fuel_capacity_t": fuel_capacity,
            }
            for name in {hull_name, hull_base_name}:
                if name:
                    hulls[normalized_name(name)] = stats
        hulls_by_company[company_id] = hulls
    return hulls_by_company


def live_spacecraft_stats(
    company_id: str,
    craft_type_key: str,
    fallback_stats: dict[str, Any],
    company_hulls: dict[str, dict[str, dict[str, float | None]]],
) -> dict[str, Any]:
    candidates: list[str] = []
    for candidate in fallback_stats.get("hull_candidates", ()):
        if isinstance(candidate, str) and candidate not in candidates:
            candidates.append(candidate)
    for candidate in SPACECRAFT_TYPE_HULL_CANDIDATES.get(craft_type_key, ()):
        if candidate not in candidates:
            candidates.append(candidate)

    hulls = company_hulls.get(company_id, {})
    for candidate in candidates:
        hull_stats = hulls.get(normalized_name(candidate))
        if hull_stats:
            merged = dict(fallback_stats)
            merged.update({key: value for key, value in hull_stats.items() if value is not None})
            merged["capacity_source"] = "save_hull"
            return merged

    merged = dict(fallback_stats)
    merged["capacity_source"] = "reference"
    return merged


def build_craft_facts(
    save: dict[str, Any],
    repo_root: Path,
    mission_facts: list[MissionFact] | None = None,
    included_companies: set[str] | None = None,
    technology_reference: TechReferenceCatalog | None = None,
    tech_unlock_facts: list[TechUnlockFact] | None = None,
) -> list[CraftFact]:
    buildables, resources = load_reference_maps(repo_root)
    spacecraft_stats = load_spacecraft_stats(repo_root)
    object_names, _object_types = build_object_metadata(save, repo_root)
    companies = [company for company in list_content(save.get("companyDataSave")) if isinstance(company, dict)]
    current_time = extract_datetime(save.get("currentTime"))
    if mission_facts is None:
        mission_facts = build_mission_facts(companies, object_names, resources, buildables, current_time)
    mission_index = build_mission_index(mission_facts)
    company_hulls = build_company_hull_stats(companies)

    facts: list[CraftFact] = []
    for company in companies:
        company_id = str(id_value(company.get("companyID"), ""))
        if included_companies is not None and company_id not in included_companies:
            continue
        for craft in list_content(company.get("spacecrafts")):
            if not isinstance(craft, dict):
                continue
            craft_id = craft.get("ID")
            craft_id_int = craft_id if isinstance(craft_id, int) else -1
            mission = mission_index.get((company_id, craft_id_int))
            craft_type_key = game_key(craft.get("spacecraftType"))
            stats = live_spacecraft_stats(company_id, craft_type_key, spacecraft_stats.get(craft_type_key, {}), company_hulls)
            mission_raw = mission.raw if mission else {}
            mission_cargo = mission_raw.get("cargoAllData") if mission_raw else None
            active_cargo_all = mission_cargo if mission_cargo else craft.get("cargoAllData")
            onboard_cargo = cargo_summary(craft.get("cargoAllData"), resources, buildables)
            onboard_fuel = fuel_summary(craft.get("cargoAllData"), resources)
            active_cargo_mass = cargo_mass(active_cargo_all)
            active_fuel_mass = fuel_mass(active_cargo_all)
            cargo_capacity = stats.get("cargo_capacity_t") if isinstance(stats.get("cargo_capacity_t"), (int, float)) else None
            fuel_capacity = stats.get("fuel_capacity_t") if isinstance(stats.get("fuel_capacity_t"), (int, float)) else None
            raw_cargo_capacity = cargo_capacity
            raw_fuel_capacity = fuel_capacity
            planned_total_fuel = mission.planned_total_fuel if mission else None
            optimal_fuel = mission.optimal_fuel if mission else None
            capacity_source = str(stats.get("capacity_source") or "")
            unlocked_modifiers = unlocked_reference_modifiers(technology_reference, tech_unlock_facts, company_id)
            cargo_capacity, cargo_adjustment = spacecraft_percent_capacity_adjustment(
                unlocked_modifiers,
                target_key=craft_type_key,
                modifier_type="component_cargo_capacity_percent",
                raw_value=raw_cargo_capacity,
                source=capacity_source,
            )
            fuel_adjustment = None
            capacity_adjustment = cargo_adjustment or fuel_adjustment
            if capacity_adjustment:
                capacity_source = f"{capacity_source}+tech_reference"
            capacity_metrics = build_capacity_metrics(
                cargo_mass_used=active_cargo_mass,
                cargo_capacity=cargo_capacity,
                raw_cargo_capacity=raw_cargo_capacity,
                fuel_mass=active_fuel_mass,
                fuel_capacity=fuel_capacity,
                raw_fuel_capacity=raw_fuel_capacity,
                planned_total_fuel=planned_total_fuel,
                optimal_fuel=optimal_fuel,
                life_support_loaded_value=life_support_loaded(active_cargo_all),
                capacity_source=capacity_source,
                tech_adjustment=capacity_adjustment,
            )
            status = mission.status if mission else "Idle"
            active_assignment = bool(mission and mission.status not in {"Arrived", "Canceled"})
            transfer = mission.transfer if mission and mission.mission_type == "cyclical" else transfer_summary(mission_raw, stats)
            current_object_id = craft.get("idObjectInfo") if isinstance(craft.get("idObjectInfo"), int) else None
            true_object_id = craft.get("idObjectTruly") if isinstance(craft.get("idObjectTruly"), int) else None
            category = str(stats.get("category") or "")
            capacity_semantics = str(stats.get("capacity_semantics") or CAPACITY_SEMANTICS_NORMAL)
            launch_status = launchcraft_status(stats)
            fuel_resource = (
                mission.fuel_resource_key
                if mission and mission.fuel_resource_key
                else str(stats.get("fuel_type_id") or "") or fuel_resource_key(craft.get("cargoAllData"))
            )
            facts.append(
                CraftFact(
                    company=company_id,
                    craft_id=craft_id_int,
                    craft_name=craft.get("spacecraftName") or f"{buildables.get(craft_type_key, friendly_key(craft_type_key))} {craft_id}",
                    spacecraft_type_key=craft_type_key,
                    spacecraft_type=buildables.get(craft_type_key, friendly_key(craft_type_key) or craft_type_key),
                    current_object_id=current_object_id,
                    current_object=object_label(current_object_id, object_names),
                    true_object_id=true_object_id,
                    true_object=object_label(true_object_id, object_names),
                    status=status,
                    has_active_assignment=active_assignment,
                    active_assignment_key=mission.mission_key if active_assignment and mission else "",
                    mission_id=mission.mission_id if mission else "",
                    mission_type=mission.mission_type if mission else "",
                    route=mission.route if mission else "",
                    route_type=mission.route_type if mission else "",
                    departure=mission.departure if mission else "",
                    arrival=mission.arrival if mission else "",
                    departure_dt=mission.departure_dt if mission else None,
                    arrival_dt=mission.arrival_dt if mission else None,
                    timing=mission.timing if mission else build_timing_metrics(None, None, current_time),
                    mission_timing=timing_summary(mission.departure_dt if mission else None, mission.arrival_dt if mission else None, current_time),
                    cargo=(mission.cargo if mission else "") or onboard_cargo,
                    fuel=(mission.fuel if mission else "") or onboard_fuel,
                    cargo_mass=active_cargo_mass,
                    fuel_mass=active_fuel_mass,
                    fuel_resource_key=fuel_resource,
                    planned_total_fuel=planned_total_fuel,
                    optimal_fuel=optimal_fuel,
                    capacity_metrics=capacity_metrics,
                    cargo_capacity=capacity_metrics.cargo_capacity,
                    fuel_capacity=capacity_metrics.fuel_capacity,
                    capacity_source=capacity_metrics.capacity_source,
                    fuel_type_name=str(stats.get("fuel_type_name") or ""),
                    propulsion_class=str(stats.get("propulsion_class") or ""),
                    surface_capable=bool(stats.get("surface_capable")),
                    orbit_only=bool(stats.get("orbit_only")),
                    continuous_burn_capable=bool(stats.get("continuous_burn_capable")),
                    construction_mode=str(stats.get("construction_mode") or ""),
                    category=category,
                    is_launchcraft=category == "Launchcraft",
                    capacity_semantics=capacity_semantics,
                    launchcraft_status=launch_status,
                    transfer=transfer,
                    fuel_plan=fuel_plan_summary(
                        capacity_metrics.planned_total_fuel,
                        capacity_metrics.optimal_fuel,
                        capacity_metrics.saved_residual_or_onboard_fuel,
                        capacity_metrics.fuel_capacity,
                        status,
                    ),
                    capacity=capacity_summary_for_semantics(
                        capacity_metrics.cargo_mass_used,
                        capacity_metrics.cargo_capacity,
                        capacity_semantics,
                    ),
                    warnings=movement_warnings(
                        status=status,
                        mission_cargo_mass=active_cargo_mass,
                        capacity=cargo_capacity,
                        capacity_semantics=capacity_semantics,
                    ),
                    raw=craft,
                    mission_raw=mission_raw if mission_raw else None,
                )
            )

    facts.sort(key=lambda fact: (fact.company, fact.status, fact.spacecraft_type, fact.craft_id))
    return facts
