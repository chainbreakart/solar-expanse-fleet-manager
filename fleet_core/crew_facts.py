from __future__ import annotations

from datetime import datetime

from .fact_model import CargoFact, CraftFact, CrewMetric, TechReferenceCatalog, TechUnlockFact
from .mission_facts import timing_summary
from .normalizer_utils import ROUTE_LOAD_STATUSES, friendly_key
from .technology_adjustments import transport_capacity_adjustment, unlocked_reference_modifiers

CREW_METRIC_STATUSES = ROUTE_LOAD_STATUSES | {"Cyclical paused"}
CREW_MODULE_TYPE_LABELS = {
    "module_crew_compartment": "Type-S",
    "module_crew_medium": "Type-M",
    "module_crew_large": "Type-L",
}


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
    technology_reference: TechReferenceCatalog | None = None,
    tech_unlock_facts: list[TechUnlockFact] | None = None,
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
        raw_capacity_per_unit = capacity_per_unit
        unlocked_modifiers = unlocked_reference_modifiers(technology_reference, tech_unlock_facts, cargo.company)
        capacity_per_unit, capacity_adjustment = transport_capacity_adjustment(
            unlocked_modifiers,
            module_key=cargo.module_key,
            raw_capacity=raw_capacity_per_unit,
        )
        reference_seats = crew_reference_seats(cargo, capacity_per_unit)
        raw_reference_seats = crew_reference_seats(cargo, raw_capacity_per_unit)
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
                raw_reference_seats=raw_reference_seats,
                empty_seats=empty_seats,
                state=state,
                life_support_carriage=life_support_by_mission.get(cargo.mission_key, cargo.life_support),
                row_life_support=cargo.life_support,
                location=cargo.list_label,
                warnings="",
                source_cargo_key=cargo.cargo_key,
                tech_adjustment=capacity_adjustment,
            )
        )

    return sorted(metrics, key=lambda item: (item.arrival or "9999", item.company, item.mission_id, item.crew_key))
