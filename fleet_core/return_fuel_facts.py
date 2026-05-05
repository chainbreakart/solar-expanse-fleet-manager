from __future__ import annotations

from .fact_model import CargoFact, CraftFact, MissionFact, ObjectFact, ResourceStockFact, ReturnFuelMetric
from .production_facts import friendly_key, object_label

ROUTE_ACTIVE_STATUSES = {"En route", "Cyclical"}
ROUTE_PLANNED_STATUSES = {"Planned"}
ROUTE_LOAD_STATUSES = ROUTE_ACTIVE_STATUSES | ROUTE_PLANNED_STATUSES


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
        immediate_stock = (
            stocks.get((craft.company, immediate_object_id, fuel_resource_key), 0.0)
            if immediate_object_id is not None
            else 0.0
        )
        surface_stock = (
            stocks.get((craft.company, surface_object_id, fuel_resource_key), 0.0)
            if surface_object_id is not None
            else 0.0
        )
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
                destination=object_facts.get(mission.target_id).label
                if mission.target_id in object_facts
                else object_label(mission.target_id, {}),
                immediate_stock_object_id=immediate_object_id,
                immediate_stock_object=object_facts.get(immediate_object_id).label
                if immediate_object_id in object_facts
                else "",
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
