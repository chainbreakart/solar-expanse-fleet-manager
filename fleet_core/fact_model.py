from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
    raw_cargo_capacity: float | None
    cargo_free: float | None
    cargo_percent: float | None
    fuel_mass: float
    fuel_capacity: float | None
    raw_fuel_capacity: float | None
    fuel_free: float | None
    fuel_tank_percent: float | None
    planned_total_fuel: float | None
    optimal_fuel: float | None
    saved_residual_or_onboard_fuel: float
    life_support_loaded: float
    capacity_source: str
    tech_adjustment: "TechAdjustedValue | None" = None


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
    colonization_support_category: str
    colonization_support_reason: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class CargoManifestDetail:
    name: str
    kind: str
    list_label: str
    mass: float
    resource_key: str
    module_key: str
    colonization_support_category: str
    colonization_support_reason: str


@dataclass(frozen=True)
class CargoFlightMetric:
    flight_key: str
    mission_key: str
    mission_id: str
    company: str
    status: str
    craft_ids: tuple[int, ...]
    craft_names: tuple[str, ...]
    route: str
    source_id: int | None
    target_id: int | None
    source: str
    destination: str
    departure: str
    arrival: str
    departure_dt: datetime | None
    arrival_dt: datetime | None
    total_tons: float
    fuel_tons: float
    colonization_support_tons: float
    colonization_support_items: int
    colonization_support_categories: tuple[tuple[str, float], ...]
    item_count: int
    cargo_totals: tuple[tuple[str, float], ...]
    kind_counts: tuple[tuple[str, int], ...]
    details: tuple[CargoManifestDetail, ...]


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
    raw_reference_seats: int | None
    empty_seats: int | None
    state: str
    life_support_carriage: float
    row_life_support: float
    location: str
    warnings: str
    source_cargo_key: str
    tech_adjustment: "TechAdjustedValue | None" = None


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
class TechUnlockFact:
    company: str
    research_id: str
    display_name: str
    category: str
    status: str
    progress: float | None
    unlock_date: datetime | None
    source_field: str
    source_path: str
    confidence: str
    raw: dict[str, Any] | str | None


@dataclass(frozen=True)
class TechModifierFact:
    company: str
    research_id: str
    display_name: str
    category: str
    status: str
    target_type: str
    target_key: str
    modifier_type: str
    raw_value: str
    adjusted_value: float | None
    additive_value: float | None
    multiplier: float | None
    source_field: str
    source_path: str
    confidence: str
    raw: dict[str, Any] | str | None


@dataclass(frozen=True)
class TechReferenceRow:
    research_id: str
    title: str
    category: str
    prerequisite_chain: tuple[str, ...]
    unlocked_spacecraft: tuple[str, ...]
    unlocked_facilities: tuple[str, ...]
    unlocked_modules: tuple[str, ...]
    unlocked_resources: tuple[str, ...]
    source: str
    confidence: str


@dataclass(frozen=True)
class TechReferenceModifier:
    research_id: str
    title: str
    category: str
    target_type: str
    target_key: str
    modifier_type: str
    raw_value: str
    numeric_value: float | None
    multiplier: float | None
    source: str
    confidence: str


@dataclass(frozen=True)
class TechReferenceCatalog:
    rows: tuple[TechReferenceRow, ...]
    modifiers: tuple[TechReferenceModifier, ...]
    by_research_id: dict[str, TechReferenceRow]
    modifiers_by_research_id: dict[str, tuple[TechReferenceModifier, ...]]


@dataclass(frozen=True)
class TechAdjustedValue:
    raw_value: float | None
    adjusted_value: float | None
    multiplier: float | None
    source: str
    confidence: str
    basis: str


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
    tech_adjustment: TechAdjustedValue | None = None


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
    capacity_semantics: str
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
    raw_added_supply_demand_per_day: float
    projected_supply_outtake_per_day: float
    projected_supply_net_per_day: float
    supply_runway_days: float | None
    severity: str
    status: str
    message: str
    details: tuple[str, ...]
    tech_adjustment: TechAdjustedValue | None = None


@dataclass(frozen=True)
class PopulationDestinationMetric:
    destination_key: str
    company: str
    destination_id: int | None
    destination: str
    status: str
    message: str
    details: tuple[str, ...]
    inbound_people: int
    current_population: float
    projected_population: float
    completed_housing: float
    queued_housing: float
    arriving_housing: float
    housing_gap: float
    supply_stock: float
    supply_intake_per_day: float
    projected_supply_outtake_per_day: float
    projected_supply_net_per_day: float
    supply_runway_days: float | None
    next_arrival: str
    next_arrival_dt: datetime | None


@dataclass(frozen=True)
class PopulationFlightMetric:
    flight_key: str
    mission_key: str
    mission_id: str
    company: str
    status: str
    craft_names: tuple[str, ...]
    people: int
    empty_seats: int
    loaded_modules: int
    empty_modules: int
    life_support: float
    route: str
    source: str
    destination: str
    departure: str
    arrival: str
    departure_dt: datetime | None
    arrival_dt: datetime | None
    duration_days: float | None
    readiness_status: str
    readiness_message: str
    readiness_details: tuple[str, ...]


@dataclass(frozen=True)
class PopulationPlaceMetric:
    place_key: str
    company: str
    object_id: int
    place: str
    object_type: str
    relationship: str
    status: str
    message: str
    details: tuple[str, ...]
    current_population: float
    completed_housing: float
    queued_housing: float
    free_housing: float
    housing_gap: float
    supply_stock: float
    supply_intake_per_day: float
    supply_outtake_per_day: float
    supply_net_per_day: float
    supply_modifier: float
    supply_modifier_basis: str
    supply_runway_days: float | None
    inbound_people: int


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


@dataclass(frozen=True)
class AttentionRow:
    attention_key: str
    severity: str
    category: str
    source: str
    company: str
    title: str
    message: str
    route: str
    body: str
    craft_id: int | None
    craft_name: str
    mission_key: str
    drilldown: str
    event_date: str
    details: tuple[str, ...]
