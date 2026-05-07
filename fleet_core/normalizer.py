from __future__ import annotations

from pathlib import Path
from typing import Any

from .attention import (
    build_attention_rows,
    capacity_attention_rows,
    cargo_attention_rows,
    fuel_attention_rows,
    population_attention_rows,
    save_data_attention_rows,
    technology_reference_attention_rows,
)
from .body_facts import build_body_metrics
from .capacity_facts import (
    build_capacity_metrics,
    capacity_summary,
    capacity_summary_for_semantics,
    fuel_plan_summary,
    metric_free,
    metric_percent,
    movement_warnings,
)
from .cargo_facts import build_cargo_facts, cargo_mass, cargo_summary, fuel_mass, fuel_resource_key, life_support_loaded
from .craft_facts import (
    build_company_hull_stats,
    build_craft_facts,
    build_craft_type_index,
    launchcraft_status,
    live_spacecraft_stats,
)
from .crew_facts import (
    CREW_METRIC_STATUSES,
    CREW_MODULE_TYPE_LABELS,
    build_crew_metrics,
    crew_compartment_type,
    crew_reference_seats,
    transport_capacity_value,
)
from .fact_model import (
    AttentionRow,
    BodyMetric,
    CapacityMetrics,
    CargoFact,
    CargoFlightMetric,
    CargoManifestDetail,
    CraftFact,
    CrewMetric,
    FleetRow,
    MissionFact,
    ObjectFact,
    PopulationDestinationMetric,
    PopulationFlightMetric,
    PopulationPlaceMetric,
    PopulationReadinessMetric,
    ProductionBalanceMetric,
    ResourceStockFact,
    ReturnFuelMetric,
    RouteMetric,
    TechAdjustedValue,
    TechModifierFact,
    TechReferenceCatalog,
    TechReferenceModifier,
    TechReferenceRow,
    TechUnlockFact,
    TimingMetrics,
)
from .mission_facts import (
    build_mission_facts,
    build_mission_index,
    build_timing_metrics,
    fuel_summary,
    mission_craft_ids,
    timing_summary,
    transfer_summary,
)
from .normalizer_utils import (
    DOTNET_EPOCH,
    FILETIME_EPOCH,
    ROUTE_ACTIVE_STATUSES,
    ROUTE_LOAD_STATUSES,
    ROUTE_PLANNED_STATUSES,
    as_bool,
    as_float,
    as_int,
    enum_name,
    extract_datetime,
    fmt_dt,
    fmt_num,
    fmt_rate,
    friendly_key,
    game_key,
    id_value,
    list_content,
    normalized_name,
    pct,
    ref_value,
)
from .object_facts import build_object_facts, build_object_metadata, build_object_names, object_label
from .population_facts import (
    build_population_readiness_metrics,
    effective_supply_modifier,
    housing_capacity_for_row,
    load_habitat_capacity_map,
    modeled_surface_supply_demand,
    object_company_rows,
    stock_fact_lookup,
    supply_runway_severity,
)
from .production_facts import (
    build_production_balance_metrics,
    build_resource_stock_facts,
    production_runway_days,
    production_status,
)
from .return_fuel_facts import (
    build_return_fuel_metrics,
    child_orbit_lookup,
    compatible_fuel_cargo,
    expected_onboard_fuel_for_return,
    return_fuel_warning,
    return_stock_objects,
    reverse_requirement_for,
    stock_lookup,
)
from .route_facts import build_route_metrics
from .spacecraft_reference import (
    CAPACITY_SEMANTICS_NORMAL,
    CAPACITY_SEMANTICS_ORBITAL_PAYLOAD_CONTAINER,
    ORBITAL_PAYLOAD_CONTAINER_TYPES,
    SPACECRAFT_HEAD_NAME_RE,
    SPACECRAFT_TYPE_HULL_CANDIDATES,
    capacity_semantics_for_spacecraft,
    load_reference_maps,
    load_spacecraft_stats,
    spacecraft_hull_candidates,
)
from .technology_adjustments import (
    life_support_consumption_adjustment,
    spacecraft_percent_capacity_adjustment,
    transport_capacity_adjustment,
    unlocked_reference_modifiers,
)


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
