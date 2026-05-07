from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from .fact_model import CargoFact, CargoFlightMetric, CargoManifestDetail, CraftFact, MissionFact, ObjectFact
from .normalizer_utils import ROUTE_LOAD_STATUSES, as_float, fmt_num, friendly_key, game_key, id_value, list_content

CARGO_TRANSIT_KINDS = {"resource", "module", "crew_module", "fuel", "unknown"}
CARGO_LIST_LABELS = {
    "listCargoData": "main cargo",
    "listCargoDataToOrbit": "to orbit",
    "listCargoGravityAssists": "gravity assist",
}
FUEL_RESOURCE_KEYS = {"id_resource_fuel", "id_resource_noblegas", "id_resource_hydrogen", "id_resource_hel3"}
CONSTRUCTION_RESOURCE_KEYS = {
    "id_resource_alloy",
    "id_resource_chips",
    "id_resource_glass",
    "id_resource_metal",
    "id_resource_plastic",
    "id_resource_raremetal",
    "id_resource_silicon",
    "id_resource_steel",
}
HABITAT_MODULE_TOKENS = ("habitat", "0gcity", "outpost", "crew")
CONSTRUCTION_MODULE_TOKENS = ("construction", "build_", "mine", "refinery", "factory", "plant", "extractor", "power")


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


def colonization_support_classification(
    *,
    cargo_kind: str,
    resource_key: str,
    module_key: str,
    display_name: str,
) -> tuple[str, str]:
    """Classify cargo that can support a new or growing colony."""
    name = display_name.lower()
    module_text = module_key.lower()
    if resource_key == "id_resource_supply":
        return "Supply", "consumable colony sustainment stock"
    if cargo_kind == "crew_module" or any(token in module_text or token in name for token in HABITAT_MODULE_TOKENS):
        return "Habitat / crew module", "habitat or crew-capable module"
    if cargo_kind == "fuel" or resource_key in FUEL_RESOURCE_KEYS:
        return "Compatible fuel", "fuel resource that may support route continuation or local operations"
    if resource_key in CONSTRUCTION_RESOURCE_KEYS:
        return "Construction resource", "resource commonly consumed by early facilities or habitat builds"
    if module_key and any(token in module_text or token in name for token in CONSTRUCTION_MODULE_TOKENS):
        return "Outpost / build module", "module or buildable that can seed local construction or production"
    return "", ""


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
            display_name = cargo_item_display_name(item, resources, buildables)
            support_category, support_reason = colonization_support_classification(
                cargo_kind=cargo_kind,
                resource_key=resource_key,
                module_key=module_key,
                display_name=display_name,
            )
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
                    display_name=display_name,
                    mass=mass,
                    people=people,
                    life_support=as_float(item.get("lifeSupportValue")) or 0.0,
                    is_crew_module=cargo_kind == "crew_module",
                    colonization_support_category=support_category,
                    colonization_support_reason=support_reason,
                    raw=item,
                )
            )

    fuel = cargo_all.get("cargoFuel")
    if isinstance(fuel, dict):
        fuel_amount = as_float(fuel.get("cargoMass")) or 0.0
        fuel_key = game_key(fuel.get("resourceType"))
        life_support = as_float(fuel.get("lifeSupportValue")) or 0.0
        if fuel_key or fuel_amount:
            display_name = resources.get(fuel_key) or friendly_key(fuel_key) or "Fuel"
            support_category, support_reason = colonization_support_classification(
                cargo_kind="fuel",
                resource_key=fuel_key,
                module_key="",
                display_name=display_name,
            )
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
                    display_name=display_name,
                    mass=fuel_amount,
                    people=0,
                    life_support=life_support,
                    is_crew_module=False,
                    colonization_support_category=support_category,
                    colonization_support_reason=support_reason,
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
                    colonization_support_category="Supply",
                    colonization_support_reason="mission life-support carriage",
                    raw=fuel,
                )
            )

    return facts


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
