from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .odin_save_parser import FStringRef

DOTNET_EPOCH = datetime(1, 1, 1)
FILETIME_EPOCH = datetime(1601, 1, 1)

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

CARGO_LIST_LABELS = {
    "listCargoData": "main cargo",
    "listCargoDataToOrbit": "to orbit",
    "listCargoGravityAssists": "gravity assist",
}

ROUTE_ACTIVE_STATUSES = {"En route", "Cyclical"}
ROUTE_PLANNED_STATUSES = {"Planned"}
ROUTE_LOAD_STATUSES = ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES
CREW_METRIC_STATUSES = ROUTE_LOAD_STATUSES | {"Cyclical paused"}
CREW_MODULE_TYPE_LABELS = {
    "module_crew_compartment": "Type-S",
    "module_crew_medium": "Type-M",
    "module_crew_large": "Type-L",
}
SUPPLY_RESOURCE_KEY = "id_resource_supply"
HUMAN_RESOURCE_KEY = "id_resource_human"
SURFACE_LIFE_SUPPORT_MULTIPLIER = 5.0
CREW_IN_HABITATS_LIFE_SUPPORT_MULTIPLIER = 0.5
SUPPLY_TO_LIFE_SUPPORT_MULTIPLIER = 365.0
PRODUCTION_RUNWAY_WARNING_DAYS = 730
PRODUCTION_RUNWAY_URGENT_DAYS = 365
PRODUCTION_RUNWAY_CRITICAL_DAYS = 183


@dataclass(frozen=True)
class FleetRow:
    company: str
    craft_id: int
    craft_name: str
    craft_type: str
    current_object: str
    status: str
    route: str
    departure: str
    arrival: str
    cargo: str
    fuel: str
    mission_timing: str
    fuel_plan: str
    capacity: str
    transfer: str
    warnings: str
    mission_id: str


@dataclass(frozen=True)
class TimingMetrics:
    duration_days: float | None
    percent_complete: float | None
    days_until_departure: float | None
    days_until_arrival: float | None
    days_since_stale_arrival: float | None


@dataclass(frozen=True)
class CapacityMetrics:
    cargo_mass_used: float
    cargo_capacity: float | None
    cargo_free: float | None
    cargo_percent: float | None
    fuel_mass: float
    fuel_capacity: float | None
    fuel_free: float | None
    fuel_tank_percent: float | None
    planned_total_fuel: float | None
    optimal_fuel: float | None
    saved_residual_or_onboard_fuel: float
    life_support_loaded: float
    capacity_source: str


@dataclass(frozen=True)
class MissionFact:
    company: str
    mission_key: str
    mission_id: str
    mission_type: str
    raw: dict[str, Any]
    craft_ids: tuple[int, ...]
    start_id: int | None
    target_id: int | None
    route: str
    route_type: str
    status: str
    departure: str
    arrival: str
    departure_dt: datetime | None
    arrival_dt: datetime | None
    timing: TimingMetrics
    cargo: str
    fuel: str
    cargo_mass: float
    fuel_mass: float
    fuel_resource_key: str
    planned_total_fuel: float | None
    optimal_fuel: float | None
    transfer: str


@dataclass(frozen=True)
class CargoFact:
    company: str
    cargo_key: str
    source_type: str
    source_key: str
    mission_key: str
    mission_id: str
    mission_type: str
    mission_status: str
    craft_ids: tuple[int, ...]
    object_id: int | None
    route: str
    departure: str
    arrival: str
    departure_dt: datetime | None
    arrival_dt: datetime | None
    list_name: str
    list_label: str
    row_index: int
    cargo_kind: str
    resource_key: str
    module_key: str
    display_name: str
    mass: float
    people: int
    life_support: float
    is_crew_module: bool
    raw: dict[str, Any]


@dataclass(frozen=True)
class CrewMetric:
    crew_key: str
    company: str
    status: str
    mission_key: str
    mission_id: str
    craft_id: int
    craft_name: str
    craft_type: str
    route: str
    departure: str
    arrival: str
    timing: str
    cargo_item: str
    compartment_type: str
    module_key: str
    people: int
    reference_seats: int | None
    empty_seats: int | None
    state: str
    life_support_carriage: float
    row_life_support: float
    location: str
    warnings: str
    source_cargo_key: str


@dataclass(frozen=True)
class ResourceStockFact:
    company: str
    object_id: int
    object_label: str
    resource_key: str
    resource_name: str
    value: float
    intake: float
    outtake: float
    source: str


@dataclass(frozen=True)
class ProductionBalanceMetric:
    production_key: str
    company: str
    object_id: int
    object_label: str
    object_type: str
    resource_key: str
    resource_name: str
    stock: float
    intake_per_day: float
    outtake_per_day: float
    net_per_day: float
    runway_days: float | None
    status: str
    status_basis: str
    source: str


@dataclass(frozen=True)
class ObjectFact:
    object_id: int
    display_name: str
    label: str
    object_type: str
    object_type_id: int | None
    parent_id: int | None
    parent_name: str
    parent_label: str
    relationship: str
    is_orbit: bool
    is_surface: bool
    can_mine: bool | None
    path_id: int | None
    owner_companies: tuple[str, ...]
    present_craft: int
    inbound_missions: int
    outbound_missions: int
    next_arrival: str
    raw: dict[str, Any] | None


@dataclass(frozen=True)
class CraftFact:
    company: str
    craft_id: int
    craft_name: str
    spacecraft_type_key: str
    spacecraft_type: str
    current_object_id: int | None
    current_object: str
    true_object_id: int | None
    true_object: str
    status: str
    has_active_assignment: bool
    active_assignment_key: str
    mission_id: str
    mission_type: str
    route: str
    route_type: str
    departure: str
    arrival: str
    departure_dt: datetime | None
    arrival_dt: datetime | None
    timing: TimingMetrics
    mission_timing: str
    cargo: str
    fuel: str
    cargo_mass: float
    fuel_mass: float
    fuel_resource_key: str
    planned_total_fuel: float | None
    optimal_fuel: float | None
    capacity_metrics: CapacityMetrics
    cargo_capacity: float | None
    fuel_capacity: float | None
    capacity_source: str
    fuel_type_name: str
    propulsion_class: str
    surface_capable: bool
    orbit_only: bool
    continuous_burn_capable: bool
    construction_mode: str
    category: str
    is_launchcraft: bool
    launchcraft_status: str
    transfer: str
    fuel_plan: str
    capacity: str
    warnings: str
    raw: dict[str, Any]
    mission_raw: dict[str, Any] | None


@dataclass(frozen=True)
class RouteMetric:
    route_key: str
    route: str
    route_type: str
    total_craft_count: int
    active_craft_count: int
    planned_craft_count: int
    cargo_tons_in_transit: float
    people_in_transit: int
    next_departure: str
    next_arrival: str
    attention_count: int
    companies: tuple[str, ...]
    status_counts: tuple[tuple[str, int], ...]
    assigned_craft: tuple[str, ...]
    cargo_summaries: tuple[str, ...]
    fuel_plan_summaries: tuple[str, ...]
    capacity_summaries: tuple[str, ...]
    transfers: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class BodyMetric:
    object_id: int
    body: str
    object_type: str
    parent: str
    relationship: str
    companies: tuple[str, ...]
    craft_present: int
    idle_craft: int
    active_inbound_craft: int
    planned_inbound_craft: int
    outbound_craft: int
    inbound_cargo: tuple[tuple[str, float], ...]
    inbound_people: int
    outbound_people: int
    next_arrival: str
    craft_here: tuple[str, ...]
    inbound_routes: tuple[str, ...]
    outbound_routes: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class PopulationReadinessMetric:
    readiness_key: str
    company: str
    mission_key: str
    destination_id: int | None
    destination: str
    inbound_people: int
    current_population: float
    projected_population: float
    completed_housing: float
    queued_housing: float
    arriving_housing: float
    housing_gap: float
    supply_stock: float
    supply_intake_per_day: float
    supply_outtake_per_day: float
    effective_supply_modifier: float
    supply_modifier_basis: str
    added_supply_demand_per_day: float
    projected_supply_outtake_per_day: float
    projected_supply_net_per_day: float
    supply_runway_days: float | None
    severity: str
    status: str
    message: str
    details: tuple[str, ...]


@dataclass(frozen=True)
class ReturnFuelMetric:
    return_key: str
    company: str
    craft_id: int
    craft_name: str
    craft_type: str
    status: str
    route: str
    departure: str
    arrival: str
    destination_id: int | None
    destination: str
    immediate_stock_object_id: int | None
    immediate_stock_object: str
    surface_stock_object_id: int | None
    surface_stock_object: str
    fuel_resource_key: str
    fuel_type: str
    estimated_return_requirement: float | None
    return_requirement_confidence: str
    requirement_basis: str
    expected_onboard_fuel_at_arrival: float
    expected_onboard_fuel_basis: str
    compatible_fuel_cargo: float
    destination_immediate_stock: float
    destination_surface_stock: float
    lift_needed_surface_fuel: float
    immediate_return_margin: float | None
    deferred_return_margin: float | None
    warning: str


def list_content(value: Any) -> list[Any]:
    if isinstance(value, dict):
        content = value.get("$rcontent")
        return content if isinstance(content, list) else []
    return value if isinstance(value, list) else []


def id_value(value: Any, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get("id", default)
    return default


def ref_value(value: Any) -> str:
    if isinstance(value, FStringRef):
        return value.value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("id") or value.get("ID")
        if raw is not None:
            return str(raw)
    return ""


def game_key(value: Any) -> str:
    raw = ref_value(value)
    return raw.rsplit("/", 1)[-1] if raw else ""


def friendly_key(raw: Any) -> str:
    key = game_key(raw)
    prefixes = (
        "id_resource_",
        "spacecraft_",
        "module_",
        "build_",
        "id_Rocket_",
        "research_",
    )
    for prefix in prefixes:
        if key.startswith(prefix):
            key = key[len(prefix) :]
            break
    return key.replace("_", " ").strip().title() if key else ""


def normalized_name(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


def dotnet_ticks_to_datetime(ticks: Any) -> datetime | None:
    if not isinstance(ticks, int):
        return None
    try:
        return DOTNET_EPOCH + timedelta(microseconds=ticks / 10)
    except OverflowError:
        return None


def filetime_to_datetime(ticks: Any) -> datetime | None:
    if not isinstance(ticks, int):
        return None
    try:
        return FILETIME_EPOCH + timedelta(microseconds=ticks / 10)
    except OverflowError:
        return None


def extract_datetime(value: Any) -> datetime | None:
    if isinstance(value, dict):
        type_name = str(value.get("$type") or "")
        if isinstance(value.get("value"), int):
            if "JsonDateTime" in type_name:
                return filetime_to_datetime(value["value"])
            return dotnet_ticks_to_datetime(value["value"])
        values = value.get("$values")
        if isinstance(values, list) and values:
            return dotnet_ticks_to_datetime(values[0])
    return None


def fmt_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d") if value else ""


def fmt_num(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if abs(value - round(value)) < 0.005:
        return f"{value:.0f}"
    return f"{value:.1f}"


def fmt_rate(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 10:
        return fmt_num(value)
    if abs(value) >= 0.1:
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{value:.4f}".rstrip("0").rstrip(".")


def pct(part: float | None, total: float | None) -> str:
    if not isinstance(part, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return ""
    return f"{part / total * 100:.0f}%"


def as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return None
    return None


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def enum_name(value: Any, names: dict[int, str]) -> str:
    return names.get(value, str(value)) if isinstance(value, int) else ""


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

            stats[game_id] = {
                "asset_name": row.get("asset_name") or game_id,
                "category": row.get("category") or "",
                "head_name": row.get("head_name") or "",
                "cargo_capacity_t": float_field("cargo_capacity_t"),
                "fuel_capacity_t": float_field("fuel_capacity_t"),
                "propulsion_class": row.get("propulsion_class") or "",
                "fuel_type_id": row.get("engine_fuel_type_id") or "",
                "fuel_type_name": row.get("engine_fuel_type_name") or "",
                "surface_capable": (row.get("surface_capable") or "").lower() == "true",
                "orbit_only": (row.get("orbit_only") or "").lower() == "true",
                "construction_mode": row.get("construction_mode") or "",
                "continuous_burn_capable": (row.get("continuous_burn_capable") or "").lower() == "true",
            }
    return stats


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
        object_id = id_value(obj.get("IDObjectInfo")) if isinstance(obj, dict) else None
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


def build_object_facts(
    save: dict[str, Any],
    repo_root: Path,
    mission_facts: list[MissionFact] | None = None,
    included_companies: set[str] | None = None,
) -> dict[int, ObjectFact]:
    buildables, resources = load_reference_maps(repo_root)
    object_names, object_types = build_object_metadata(save, repo_root)
    reference = load_object_reference(repo_root)
    companies = [company for company in list_content(save.get("companyDataSave")) if isinstance(company, dict)]
    current_time = extract_datetime(save.get("currentTime"))
    if mission_facts is None:
        mission_facts = build_mission_facts(companies, object_names, resources, buildables, current_time)

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
        object_id = id_value(obj.get("IDObjectInfo"))
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


def build_object_names(save: dict[str, Any], repo_root: Path) -> dict[int, str]:
    names, _ = build_object_metadata(save, repo_root)
    return names


def object_label(object_id: Any, names: dict[int, str]) -> str:
    if not isinstance(object_id, int) or object_id < 0:
        return "-"
    name = names.get(object_id)
    return f"{name} ({object_id})" if name else f"Object {object_id}"


def cargo_summary(cargo_all: Any, resources: dict[str, str], buildables: dict[str, str]) -> str:
    if not isinstance(cargo_all, dict):
        return ""

    parts: list[str] = []
    for list_name in ("listCargoData", "listCargoDataToOrbit", "listCargoGravityAssists"):
        for item in list_content(cargo_all.get(list_name)):
            if not isinstance(item, dict):
                continue
            mass = item.get("cargoMass")
            crew = item.get("crewValue") if item.get("crew") else None
            resource_key = game_key(item.get("resourceType"))
            module_key = game_key(item.get("moduleData"))
            name = resources.get(resource_key) or buildables.get(module_key) or friendly_key(resource_key or module_key)
            if not name:
                continue
            suffix = ""
            if isinstance(crew, int) and crew:
                suffix = f", {crew:,} crew"
            parts.append(f"{name} {fmt_num(mass)}t{suffix}".strip())

    return "; ".join(parts)


def cargo_item_display_name(item: dict[str, Any], resources: dict[str, str], buildables: dict[str, str]) -> str:
    resource_key = game_key(item.get("resourceType"))
    module_key = game_key(item.get("moduleData"))
    if item.get("crew") and not resource_key and not module_key:
        return "Crew cargo"
    return resources.get(resource_key) or buildables.get(module_key) or friendly_key(resource_key or module_key) or "Cargo"


def cargo_people_count(item: dict[str, Any], cargo_kind: str, mass: float) -> int:
    crew_value = item.get("crewValue")
    people = int(crew_value) if isinstance(crew_value, int) else 0
    if cargo_kind == "human" and people == 0 and mass > 0:
        return int(mass)
    return people


def classify_cargo_item(item: dict[str, Any], crew_module_keys: set[str] | None = None) -> str:
    resource_key = game_key(item.get("resourceType"))
    module_key = game_key(item.get("moduleData"))
    if resource_key == "id_resource_human":
        return "human"
    if bool(item.get("crew")) or module_key in (crew_module_keys or set()):
        return "crew_module"
    if module_key:
        return "module"
    if resource_key:
        return "resource"
    return "unknown"


def cargo_facts_from_cargo_all(
    cargo_all: Any,
    *,
    company_id: str,
    source_type: str,
    source_key: str,
    mission: MissionFact | None,
    craft_ids: tuple[int, ...],
    object_id: int | None,
    resources: dict[str, str],
    buildables: dict[str, str],
    crew_module_keys: set[str] | None = None,
) -> list[CargoFact]:
    if not isinstance(cargo_all, dict):
        return []

    facts: list[CargoFact] = []
    mission_key = mission.mission_key if mission else ""
    mission_id = mission.mission_id if mission else ""
    mission_type = mission.mission_type if mission else ""
    mission_status = mission.status if mission else ""
    route = mission.route if mission else ""
    departure = mission.departure if mission else ""
    arrival = mission.arrival if mission else ""
    departure_dt = mission.departure_dt if mission else None
    arrival_dt = mission.arrival_dt if mission else None

    for list_name, list_label in CARGO_LIST_LABELS.items():
        for index, item in enumerate(list_content(cargo_all.get(list_name))):
            if not isinstance(item, dict):
                continue
            mass = as_float(item.get("cargoMass")) or 0.0
            resource_key = game_key(item.get("resourceType"))
            module_key = game_key(item.get("moduleData"))
            cargo_kind = classify_cargo_item(item, crew_module_keys)
            people = cargo_people_count(item, cargo_kind, mass)
            facts.append(
                CargoFact(
                    company=company_id,
                    cargo_key=f"{source_key}:{list_name}:{index}",
                    source_type=source_type,
                    source_key=source_key,
                    mission_key=mission_key,
                    mission_id=mission_id,
                    mission_type=mission_type,
                    mission_status=mission_status,
                    craft_ids=craft_ids,
                    object_id=object_id,
                    route=route,
                    departure=departure,
                    arrival=arrival,
                    departure_dt=departure_dt,
                    arrival_dt=arrival_dt,
                    list_name=list_name,
                    list_label=list_label,
                    row_index=index,
                    cargo_kind=cargo_kind,
                    resource_key=resource_key,
                    module_key=module_key,
                    display_name=cargo_item_display_name(item, resources, buildables),
                    mass=mass,
                    people=people,
                    life_support=as_float(item.get("lifeSupportValue")) or 0.0,
                    is_crew_module=cargo_kind == "crew_module",
                    raw=item,
                )
            )

    fuel = cargo_all.get("cargoFuel")
    if isinstance(fuel, dict):
        fuel_amount = as_float(fuel.get("cargoMass")) or 0.0
        fuel_key = game_key(fuel.get("resourceType"))
        life_support = as_float(fuel.get("lifeSupportValue")) or 0.0
        if fuel_key or fuel_amount:
            facts.append(
                CargoFact(
                    company=company_id,
                    cargo_key=f"{source_key}:cargoFuel:0",
                    source_type=source_type,
                    source_key=source_key,
                    mission_key=mission_key,
                    mission_id=mission_id,
                    mission_type=mission_type,
                    mission_status=mission_status,
                    craft_ids=craft_ids,
                    object_id=object_id,
                    route=route,
                    departure=departure,
                    arrival=arrival,
                    departure_dt=departure_dt,
                    arrival_dt=arrival_dt,
                    list_name="cargoFuel",
                    list_label="fuel",
                    row_index=0,
                    cargo_kind="fuel",
                    resource_key=fuel_key,
                    module_key="",
                    display_name=resources.get(fuel_key) or friendly_key(fuel_key) or "Fuel",
                    mass=fuel_amount,
                    people=0,
                    life_support=life_support,
                    is_crew_module=False,
                    raw=fuel,
                )
            )
        if life_support:
            facts.append(
                CargoFact(
                    company=company_id,
                    cargo_key=f"{source_key}:lifeSupport:0",
                    source_type=source_type,
                    source_key=source_key,
                    mission_key=mission_key,
                    mission_id=mission_id,
                    mission_type=mission_type,
                    mission_status=mission_status,
                    craft_ids=craft_ids,
                    object_id=object_id,
                    route=route,
                    departure=departure,
                    arrival=arrival,
                    departure_dt=departure_dt,
                    arrival_dt=arrival_dt,
                    list_name="cargoFuel",
                    list_label="life support",
                    row_index=0,
                    cargo_kind="life_support",
                    resource_key=fuel_key,
                    module_key="",
                    display_name="Life support",
                    mass=0.0,
                    people=0,
                    life_support=life_support,
                    is_crew_module=False,
                    raw=fuel,
                )
            )

    return facts


def cargo_mass(cargo_all: Any) -> float:
    if not isinstance(cargo_all, dict):
        return 0.0
    total = 0.0
    for list_name in ("listCargoData", "listCargoDataToOrbit", "listCargoGravityAssists"):
        for item in list_content(cargo_all.get(list_name)):
            if not isinstance(item, dict):
                continue
            mass = as_float(item.get("cargoMass"))
            if mass:
                total += mass
    return total


def fuel_mass(cargo_all: Any) -> float:
    if not isinstance(cargo_all, dict):
        return 0.0
    fuel = cargo_all.get("cargoFuel")
    if not isinstance(fuel, dict):
        return 0.0
    return as_float(fuel.get("cargoMass")) or 0.0


def fuel_resource_key(cargo_all: Any) -> str:
    if not isinstance(cargo_all, dict):
        return ""
    fuel = cargo_all.get("cargoFuel")
    if not isinstance(fuel, dict):
        return ""
    return game_key(fuel.get("resourceType"))


def life_support_loaded(cargo_all: Any) -> float:
    if not isinstance(cargo_all, dict):
        return 0.0
    total = 0.0
    for list_name in (*CARGO_LIST_LABELS, "cargoFuel"):
        if list_name == "cargoFuel":
            items = [cargo_all.get("cargoFuel")]
        else:
            items = list_content(cargo_all.get(list_name))
        for item in items:
            if not isinstance(item, dict):
                continue
            total += as_float(item.get("lifeSupportValue")) or 0.0
    return total


def metric_percent(part: float | None, total: float | None) -> float | None:
    if not isinstance(part, (int, float)) or not isinstance(total, (int, float)) or total <= 0:
        return None
    return float(part) / float(total) * 100.0


def metric_free(capacity: float | None, used: float) -> float | None:
    if not isinstance(capacity, (int, float)):
        return None
    return float(capacity) - used


def build_capacity_metrics(
    *,
    cargo_mass_used: float,
    cargo_capacity: float | None,
    fuel_mass: float,
    fuel_capacity: float | None,
    planned_total_fuel: float | None,
    optimal_fuel: float | None,
    life_support_loaded_value: float,
    capacity_source: str,
) -> CapacityMetrics:
    return CapacityMetrics(
        cargo_mass_used=cargo_mass_used,
        cargo_capacity=cargo_capacity,
        cargo_free=metric_free(cargo_capacity, cargo_mass_used),
        cargo_percent=metric_percent(cargo_mass_used, cargo_capacity),
        fuel_mass=fuel_mass,
        fuel_capacity=fuel_capacity,
        fuel_free=metric_free(fuel_capacity, fuel_mass),
        fuel_tank_percent=metric_percent(fuel_mass, fuel_capacity),
        planned_total_fuel=planned_total_fuel,
        optimal_fuel=optimal_fuel,
        saved_residual_or_onboard_fuel=fuel_mass,
        life_support_loaded=life_support_loaded_value,
        capacity_source=capacity_source,
    )


def fuel_summary(cargo_all: Any, resources: dict[str, str]) -> str:
    if not isinstance(cargo_all, dict):
        return ""
    fuel = cargo_all.get("cargoFuel")
    if not isinstance(fuel, dict):
        return ""
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


def fuel_plan_summary(required: Any, optimal: Any, onboard: float, fuel_capacity: float | None, status: str) -> str:
    pieces: list[str] = []
    required_f = as_float(required)
    optimal_f = as_float(optimal)
    if required_f is not None:
        pieces.append(f"planned total {fmt_num(required_f)}t")
    if optimal_f is not None and abs(optimal_f - (required_f or 0.0)) > 0.05:
        pieces.append(f"optimal {fmt_num(optimal_f)}t")
    fuel_label = "residual" if status in {"Planned", "En route"} and required_f is not None else "onboard"
    pieces.append(f"{fuel_label} {fmt_num(onboard)}t")
    fuel_pct = pct(onboard, fuel_capacity)
    if fuel_pct:
        pieces.append(f"tank {fuel_pct}")
    return "; ".join(pieces)


def capacity_summary(used: float, capacity: float | None) -> str:
    if capacity is None or capacity <= 0:
        return f"{fmt_num(used)}t"
    return f"{fmt_num(used)} / {fmt_num(capacity)}t ({pct(used, capacity)})"


def transfer_summary(mission: dict[str, Any], stats: dict[str, Any]) -> str:
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


def launchcraft_status(stats: dict[str, Any]) -> str:
    if stats.get("category") == "Launchcraft":
        return "Launchcraft"
    if stats.get("surface_capable"):
        return "Surface-capable"
    if stats.get("orbit_only"):
        return "Orbit-only"
    return ""


def movement_warnings(
    status: str,
    mission_cargo_mass: float,
    capacity: float | None,
) -> str:
    warnings: list[str] = []
    if status in {"Arrived", "Canceled"}:
        return ""
    return "; ".join(warnings)


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


def build_cargo_facts(
    companies: list[dict[str, Any]],
    mission_facts: list[MissionFact],
    resources: dict[str, str],
    buildables: dict[str, str],
    crew_module_keys: set[str] | None = None,
) -> list[CargoFact]:
    facts: list[CargoFact] = []
    for mission in mission_facts:
        if mission.mission_type != "mission":
            continue
        facts.extend(
            cargo_facts_from_cargo_all(
                mission.raw.get("cargoAllData"),
                company_id=mission.company,
                source_type="mission",
                source_key=mission.mission_key,
                mission=mission,
                craft_ids=mission.craft_ids,
                object_id=None,
                resources=resources,
                buildables=buildables,
                crew_module_keys=crew_module_keys,
            )
        )

    for company in companies:
        if not isinstance(company, dict):
            continue
        company_id = str(id_value(company.get("companyID"), ""))
        for craft in list_content(company.get("spacecrafts")):
            if not isinstance(craft, dict):
                continue
            craft_id = craft.get("ID")
            if not isinstance(craft_id, int):
                continue
            object_id = craft.get("idObjectInfo") if isinstance(craft.get("idObjectInfo"), int) else None
            facts.extend(
                cargo_facts_from_cargo_all(
                    craft.get("cargoAllData"),
                    company_id=company_id,
                    source_type="craft",
                    source_key=f"craft:{company_id}:{craft_id}",
                    mission=None,
                    craft_ids=(craft_id,),
                    object_id=object_id,
                    resources=resources,
                    buildables=buildables,
                    crew_module_keys=crew_module_keys,
                )
            )
    return facts


def mission_craft_ids(mission: dict[str, Any], list_field: str = "sclistID") -> list[int]:
    craft_ids: list[int] = []
    sc_id = mission.get("scID")
    if isinstance(sc_id, int):
        craft_ids.append(sc_id)
    for craft_id in list_content(mission.get(list_field)):
        if isinstance(craft_id, int):
            craft_ids.append(craft_id)
    return list(dict.fromkeys(craft_ids))


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
        hulls: dict[str, dict[str, float]] = {}
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
    candidates: list[str] = list(SPACECRAFT_TYPE_HULL_CANDIDATES.get(craft_type_key, ()))
    asset_name = str(fallback_stats.get("asset_name") or "")
    if asset_name:
        candidates.extend([asset_name, f"{asset_name} Hull"])
    head_name = str(fallback_stats.get("head_name") or "")
    if head_name:
        candidates.append(head_name)

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
            planned_total_fuel = mission.planned_total_fuel if mission else None
            optimal_fuel = mission.optimal_fuel if mission else None
            capacity_source = str(stats.get("capacity_source") or "")
            capacity_metrics = build_capacity_metrics(
                cargo_mass_used=active_cargo_mass,
                cargo_capacity=cargo_capacity,
                fuel_mass=active_fuel_mass,
                fuel_capacity=fuel_capacity,
                planned_total_fuel=planned_total_fuel,
                optimal_fuel=optimal_fuel,
                life_support_loaded_value=life_support_loaded(active_cargo_all),
                capacity_source=capacity_source,
            )
            status = mission.status if mission else "Idle"
            active_assignment = bool(mission and mission.status not in {"Arrived", "Canceled"})
            transfer = mission.transfer if mission and mission.mission_type == "cyclical" else transfer_summary(mission_raw, stats)
            current_object_id = craft.get("idObjectInfo") if isinstance(craft.get("idObjectInfo"), int) else None
            true_object_id = craft.get("idObjectTruly") if isinstance(craft.get("idObjectTruly"), int) else None
            category = str(stats.get("category") or "")
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
                    launchcraft_status=launch_status,
                    transfer=transfer,
                    fuel_plan=fuel_plan_summary(capacity_metrics.planned_total_fuel, capacity_metrics.optimal_fuel, capacity_metrics.saved_residual_or_onboard_fuel, capacity_metrics.fuel_capacity, status),
                    capacity=capacity_summary(capacity_metrics.cargo_mass_used, capacity_metrics.cargo_capacity),
                    warnings=movement_warnings(
                        status=status,
                        mission_cargo_mass=active_cargo_mass,
                        capacity=cargo_capacity,
                    ),
                    raw=craft,
                    mission_raw=mission_raw if mission_raw else None,
                )
            )

    facts.sort(key=lambda fact: (fact.company, fact.status, fact.spacecraft_type, fact.craft_id))
    return facts


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

        endpoints: list[int] = []
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


def build_resource_stock_facts(
    save: dict[str, Any],
    object_names: dict[int, str],
    resources: dict[str, str],
    included_companies: set[str] | None = None,
) -> list[ResourceStockFact]:
    facts: list[ResourceStockFact] = []
    for row in list_content(save.get("objectInfoDatas")):
        if not isinstance(row, dict):
            continue
        company = str(id_value(row.get("companyId"), ""))
        if included_companies is not None and company not in included_companies:
            continue
        object_id = row.get("id") if isinstance(row.get("id"), int) else None
        if object_id is None:
            continue
        for resource in list_content(row.get("listRowResourcesData")):
            if not isinstance(resource, dict):
                continue
            resource_key = game_key(resource.get("resourceTypeIDSave"))
            if not resource_key:
                continue
            value = as_float(resource.get("value")) or 0.0
            intake = as_float(resource.get("inTake")) or 0.0
            outtake = as_float(resource.get("outTake")) or 0.0
            if abs(value) < 0.0001 and abs(intake) < 0.0001 and abs(outtake) < 0.0001:
                continue
            facts.append(
                ResourceStockFact(
                    company=company,
                    object_id=object_id,
                    object_label=object_label(object_id, object_names),
                    resource_key=resource_key,
                    resource_name=resources.get(resource_key) or friendly_key(resource_key) or resource_key,
                    value=value,
                    intake=intake,
                    outtake=outtake,
                    source="company_stock",
                )
            )
    return sorted(facts, key=lambda fact: (fact.company, fact.object_label, fact.resource_name))


def production_runway_days(stock: float, net_per_day: float) -> float | None:
    if net_per_day >= 0:
        return None
    if stock <= 0:
        return 0.0
    return stock / abs(net_per_day)


def production_status(stock: float, net_per_day: float) -> tuple[str, str]:
    if net_per_day >= 0:
        return "Stable", "non-negative net flow"
    if stock <= 0:
        return "Critical", "stock is empty and net flow is negative"
    runway_days = stock / abs(net_per_day)
    if runway_days < PRODUCTION_RUNWAY_CRITICAL_DAYS:
        return "Critical", "less than half a year of stock remaining"
    if runway_days < PRODUCTION_RUNWAY_URGENT_DAYS:
        return "Urgent", "less than one year of stock remaining"
    if runway_days < PRODUCTION_RUNWAY_WARNING_DAYS:
        return "Warning", "less than two years of stock remaining"
    return "Monitor", "negative flow, but more than two years of stock remain"


def build_production_balance_metrics(
    resource_stock_facts: list[ResourceStockFact],
    object_facts: dict[int, ObjectFact],
) -> list[ProductionBalanceMetric]:
    metrics: list[ProductionBalanceMetric] = []
    for fact in resource_stock_facts:
        net = fact.intake - fact.outtake
        runway_days = production_runway_days(fact.value, net)
        status, status_basis = production_status(fact.value, net)
        object_fact = object_facts.get(fact.object_id)
        object_type = object_fact.object_type if object_fact else ""
        metrics.append(
            ProductionBalanceMetric(
                production_key=f"{fact.company}:{fact.object_id}:{fact.resource_key}",
                company=fact.company,
                object_id=fact.object_id,
                object_label=fact.object_label,
                object_type=object_type,
                resource_key=fact.resource_key,
                resource_name=fact.resource_name,
                stock=fact.value,
                intake_per_day=fact.intake,
                outtake_per_day=fact.outtake,
                net_per_day=net,
                runway_days=runway_days,
                status=status,
                status_basis=status_basis,
                source=fact.source,
            )
        )

    status_rank = {"Critical": 0, "Urgent": 1, "Warning": 2, "Monitor": 3, "Stable": 4}
    return sorted(
        metrics,
        key=lambda metric: (
            status_rank.get(metric.status, 9),
            metric.runway_days if metric.runway_days is not None else float("inf"),
            metric.object_label,
            metric.resource_name,
        ),
    )


def load_habitat_capacity_map(repo_root: Path) -> dict[str, float]:
    capacities: dict[str, float] = {}
    path = repo_root / "data" / "derived" / "population" / "habitat_capacities.csv"
    if not path.exists():
        return capacities
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


def runway_label(runway_days: float | None, projected_net: float) -> str:
    if projected_net >= 0 or runway_days is None:
        return "stable"
    if runway_days >= 365.0:
        return f"{fmt_num(runway_days / 365.0)}y"
    return f"{fmt_num(runway_days)}d"


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
        destination = object_facts.get(destination_id).label if destination_id in object_facts else object_label(destination_id, {})
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
        added_supply_demand = max(projected_modeled_supply - current_modeled_supply, 0.0) * supply_modifier
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
            )
        )

    return metrics


def transport_capacity_value(capacity_info: dict[str, object]) -> int | None:
    value = capacity_info.get("capacity")
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        return int(value) if value > 0 else None
    return None


def crew_reference_seats(cargo: CargoFact, capacity_per_unit: int | None) -> int | None:
    if not cargo.is_crew_module or not capacity_per_unit:
        return None
    if cargo.people <= capacity_per_unit:
        return capacity_per_unit
    units = (cargo.people + capacity_per_unit - 1) // capacity_per_unit
    return units * capacity_per_unit


def crew_compartment_type(cargo: CargoFact, display_name: str) -> str:
    if cargo.cargo_kind == "human":
        return "Direct humans"
    if cargo.module_key in CREW_MODULE_TYPE_LABELS:
        return CREW_MODULE_TYPE_LABELS[cargo.module_key]
    return display_name or friendly_key(cargo.module_key) or "Crew module"


def build_crew_metrics(
    cargo_facts: list[CargoFact],
    craft_facts: list[CraftFact],
    transport_capacities: dict[str, dict[str, object]],
    current_time: datetime | None,
) -> list[CrewMetric]:
    craft_lookup = {(craft.company, craft.craft_id): craft for craft in craft_facts}
    life_support_by_mission: dict[str, float] = {}
    for cargo in cargo_facts:
        if cargo.source_type == "mission" and cargo.cargo_kind == "life_support":
            life_support_by_mission[cargo.mission_key] = life_support_by_mission.get(cargo.mission_key, 0.0) + cargo.life_support

    metrics: list[CrewMetric] = []
    for cargo in cargo_facts:
        if cargo.source_type != "mission" or cargo.mission_status not in CREW_METRIC_STATUSES:
            continue
        if cargo.cargo_kind not in {"human", "crew_module"}:
            continue

        craft_id = cargo.craft_ids[0] if cargo.craft_ids else -1
        craft = craft_lookup.get((cargo.company, craft_id))
        capacity_info = transport_capacities.get(cargo.module_key, {})
        capacity_per_unit = transport_capacity_value(capacity_info)
        reference_seats = crew_reference_seats(cargo, capacity_per_unit)
        empty_seats = max(reference_seats - cargo.people, 0) if reference_seats is not None else None
        display_name = str(capacity_info.get("display_name") or "") or cargo.display_name

        if cargo.people > 0:
            state = "Loaded"
        elif cargo.is_crew_module:
            state = "Empty"
        else:
            state = "No people"

        metrics.append(
            CrewMetric(
                crew_key=cargo.cargo_key,
                company=cargo.company,
                status=cargo.mission_status,
                mission_key=cargo.mission_key,
                mission_id=cargo.mission_id,
                craft_id=craft_id,
                craft_name=craft.craft_name if craft else f"Mission craft {craft_id}",
                craft_type=craft.spacecraft_type if craft else "",
                route=cargo.route,
                departure=cargo.departure,
                arrival=cargo.arrival,
                timing=timing_summary(cargo.departure_dt, cargo.arrival_dt, current_time),
                cargo_item=display_name,
                compartment_type=crew_compartment_type(cargo, display_name),
                module_key=cargo.module_key,
                people=cargo.people,
                reference_seats=reference_seats,
                empty_seats=empty_seats,
                state=state,
                life_support_carriage=life_support_by_mission.get(cargo.mission_key, cargo.life_support),
                row_life_support=cargo.life_support,
                location=cargo.list_label,
                warnings="",
                source_cargo_key=cargo.cargo_key,
            )
        )

    return sorted(metrics, key=lambda item: (item.arrival or "9999", item.company, item.mission_id, item.crew_key))


def stock_lookup(resource_stock_facts: list[ResourceStockFact]) -> dict[tuple[str, int, str], float]:
    lookup: dict[tuple[str, int, str], float] = {}
    for stock in resource_stock_facts:
        key = (stock.company, stock.object_id, stock.resource_key)
        lookup[key] = lookup.get(key, 0.0) + stock.value
    return lookup


def child_orbit_lookup(object_facts: dict[int, ObjectFact]) -> dict[int, int]:
    lookup: dict[int, int] = {}
    for fact in object_facts.values():
        if fact.is_orbit and fact.parent_id is not None and fact.parent_id not in lookup:
            lookup[fact.parent_id] = fact.object_id
    return lookup


def return_stock_objects(
    destination_id: int | None,
    object_facts: dict[int, ObjectFact],
) -> tuple[int | None, int | None]:
    if destination_id is None:
        return None, None
    destination = object_facts.get(destination_id)
    if destination and destination.is_orbit:
        return destination_id, destination.parent_id
    return destination_id, None


def compatible_fuel_cargo(cargo_facts: list[CargoFact], mission_key: str, fuel_resource_key: str) -> float:
    if not fuel_resource_key:
        return 0.0
    total = 0.0
    for cargo in cargo_facts:
        if cargo.mission_key != mission_key or cargo.cargo_kind != "resource":
            continue
        if cargo.resource_key == fuel_resource_key:
            total += cargo.mass
    return total


def expected_onboard_fuel_for_return(craft: CraftFact) -> tuple[float, str]:
    saved_fuel = max(craft.capacity_metrics.saved_residual_or_onboard_fuel, 0.0)
    if craft.status == "Planned":
        required = craft.planned_total_fuel if craft.planned_total_fuel is not None else craft.optimal_fuel
        if required is None:
            return saved_fuel, "planned saved fuel; no saved requirement"
        return max(saved_fuel - required, 0.0), "planned saved fuel minus allFuelNeed"
    if craft.status in ROUTE_ACTIVE_STATUSES:
        return saved_fuel, "en route saved fuel"
    if craft.status in {"Arrived", "Idle"}:
        return saved_fuel, "current craft fuel"
    return saved_fuel, "saved fuel"


def reverse_requirement_for(
    craft: CraftFact,
    mission: MissionFact,
    mission_facts: list[MissionFact],
    craft_facts: list[CraftFact],
) -> tuple[float | None, str, str]:
    if mission.route_type == "cyclical":
        if craft.planned_total_fuel is not None:
            return craft.planned_total_fuel, "High", "cyclical route estimate"
        return None, "High", "cyclical route; no saved fuel requirement"

    reverse_missions = [
        fact
        for fact in mission_facts
        if fact.company == mission.company
        and fact.start_id == mission.target_id
        and fact.target_id == mission.start_id
        and fact.planned_total_fuel is not None
    ]
    same_craft = [
        fact
        for fact in reverse_missions
        if craft.craft_id in fact.craft_ids and fact.status in ROUTE_LOAD_STATUSES
    ]
    if same_craft:
        return same_craft[0].planned_total_fuel, "High", "explicit reverse mission"

    craft_type_by_id = {(fact.company, fact.craft_id): fact.spacecraft_type_key for fact in craft_facts}
    same_type = [
        fact
        for fact in reverse_missions
        if any(craft_type_by_id.get((fact.company, craft_id)) == craft.spacecraft_type_key for craft_id in fact.craft_ids)
    ]
    if same_type:
        same_type.sort(key=lambda fact: (fact.arrival or fact.departure or "0000"), reverse=True)
        return same_type[0].planned_total_fuel, "Medium", "same-type reverse route"

    if craft.planned_total_fuel is not None:
        return craft.planned_total_fuel, "Low", "symmetric outbound estimate"
    return None, "Unknown", "no saved return requirement"


def return_fuel_warning(immediate_margin: float | None, deferred_margin: float | None, surface_stock: float) -> str:
    if immediate_margin is None:
        return ""
    if immediate_margin >= 0:
        return ""
    if surface_stock > 0 and deferred_margin is not None and deferred_margin >= 0:
        return "Return fuel needs surface lift"
    return "Return fuel shortfall"


def build_return_fuel_metrics(
    craft_facts: list[CraftFact],
    mission_facts: list[MissionFact],
    cargo_facts: list[CargoFact],
    resource_stock_facts: list[ResourceStockFact],
    object_facts: dict[int, ObjectFact],
    resources: dict[str, str],
) -> list[ReturnFuelMetric]:
    mission_by_key = {mission.mission_key: mission for mission in mission_facts}
    stocks = stock_lookup(resource_stock_facts)
    metrics: list[ReturnFuelMetric] = []

    for craft in craft_facts:
        if not craft.has_active_assignment or craft.status not in ROUTE_LOAD_STATUSES:
            continue
        mission = mission_by_key.get(craft.active_assignment_key)
        if not mission or mission.target_id is None:
            continue
        fuel_resource_key = craft.fuel_resource_key
        if not fuel_resource_key:
            continue

        immediate_object_id, surface_object_id = return_stock_objects(mission.target_id, object_facts)
        immediate_stock = stocks.get((craft.company, immediate_object_id, fuel_resource_key), 0.0) if immediate_object_id is not None else 0.0
        surface_stock = stocks.get((craft.company, surface_object_id, fuel_resource_key), 0.0) if surface_object_id is not None else 0.0
        compatible_cargo = compatible_fuel_cargo(cargo_facts, mission.mission_key, fuel_resource_key)
        expected_onboard, expected_onboard_basis = expected_onboard_fuel_for_return(craft)
        requirement, confidence, basis = reverse_requirement_for(craft, mission, mission_facts, craft_facts)

        immediate_margin: float | None = None
        deferred_margin: float | None = None
        lift_needed = 0.0
        if requirement is not None:
            immediate_margin = expected_onboard + compatible_cargo + immediate_stock - requirement
            deferred_margin = immediate_margin + surface_stock
            if immediate_margin < 0:
                lift_needed = min(surface_stock, abs(immediate_margin)) if surface_stock > 0 else 0.0

        metrics.append(
            ReturnFuelMetric(
                return_key=f"{craft.company}:{craft.craft_id}:{craft.active_assignment_key}",
                company=craft.company,
                craft_id=craft.craft_id,
                craft_name=craft.craft_name,
                craft_type=craft.spacecraft_type,
                status=craft.status,
                route=craft.route,
                departure=craft.departure,
                arrival=craft.arrival,
                destination_id=mission.target_id,
                destination=object_facts.get(mission.target_id).label if mission.target_id in object_facts else object_label(mission.target_id, {}),
                immediate_stock_object_id=immediate_object_id,
                immediate_stock_object=object_facts.get(immediate_object_id).label if immediate_object_id in object_facts else "",
                surface_stock_object_id=surface_object_id,
                surface_stock_object=object_facts.get(surface_object_id).label if surface_object_id in object_facts else "",
                fuel_resource_key=fuel_resource_key,
                fuel_type=resources.get(fuel_resource_key) or craft.fuel_type_name or friendly_key(fuel_resource_key),
                estimated_return_requirement=requirement,
                return_requirement_confidence=confidence,
                requirement_basis=basis,
                expected_onboard_fuel_at_arrival=expected_onboard,
                expected_onboard_fuel_basis=expected_onboard_basis,
                compatible_fuel_cargo=compatible_cargo,
                destination_immediate_stock=immediate_stock,
                destination_surface_stock=surface_stock,
                lift_needed_surface_fuel=lift_needed,
                immediate_return_margin=immediate_margin,
                deferred_return_margin=deferred_margin,
                warning=return_fuel_warning(immediate_margin, deferred_margin, surface_stock),
            )
        )

    return sorted(metrics, key=lambda item: (item.arrival or "9999", item.company, item.craft_name))


def normalize_fleet(
    save: dict[str, Any],
    repo_root: Path,
    included_companies: set[str] | None = None,
) -> tuple[list[FleetRow], dict[str, str]]:
    companies = [c for c in list_content(save.get("companyDataSave")) if isinstance(c, dict)]
    current_time = extract_datetime(save.get("currentTime"))
    craft_facts = build_craft_facts(save, repo_root, included_companies=included_companies)

    rows = [
        FleetRow(
            company=fact.company,
            craft_id=fact.craft_id,
            craft_name=fact.craft_name,
            craft_type=fact.spacecraft_type,
            current_object=fact.current_object,
            status=fact.status,
            route=fact.route,
            departure=fact.departure,
            arrival=fact.arrival,
            cargo=fact.cargo,
            fuel=fact.fuel,
            mission_timing=fact.mission_timing,
            fuel_plan=fact.fuel_plan,
            capacity=fact.capacity,
            transfer=fact.transfer,
            warnings=fact.warnings,
            mission_id=fact.mission_id,
        )
        for fact in craft_facts
    ]

    meta = {
        "save_version": str(save.get("saveVersion") or ""),
        "current_time": fmt_dt(current_time),
        "companies": str(len({row.company for row in rows})),
        "raw_companies": str(len(companies)),
        "craft_count": str(len(rows)),
    }
    return rows, meta
