from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .fact_model import (
    AttentionRow,
    BodyMetric,
    CargoFact,
    CargoFlightMetric,
    CraftFact,
    CrewMetric,
    FleetRow,
    KnownResourceDepositFact,
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
    TechModifierFact,
    TechReferenceCatalog,
    TechUnlockFact,
)
from .attention import build_attention_rows
from .body_facts import build_body_metrics
from .cargo_facts import build_cargo_facts, build_cargo_flight_metrics
from .craft_facts import build_craft_facts
from .crew_facts import build_crew_metrics
from .mission_facts import build_mission_facts
from .normalizer_utils import extract_datetime, fmt_dt, game_key, id_value, list_content
from .object_facts import build_object_facts, build_object_metadata
from .odin_save_parser import SaveParseError, parse_save_file
from .population_facts import (
    build_population_destination_metrics,
    build_population_flight_metrics,
    build_population_place_metrics,
    build_population_readiness_metrics,
)
from .production_facts import build_production_balance_metrics, build_resource_stock_facts
from .resource_deposit_facts import build_known_resource_deposit_facts
from .reference_data import load_technology_reference_catalog, load_transport_capacities
from .return_fuel_facts import build_return_fuel_metrics
from .route_facts import build_route_metrics
from .save_finder import SaveSlot
from .spacecraft_reference import load_reference_maps
from .technology_facts import build_tech_facts


@dataclass(frozen=True)
class SaveAnalysis:
    slot: SaveSlot
    repo_root: Path
    save: dict[str, Any]
    player_company: str | None
    player_company_source: str
    player_company_authoritative: bool
    company_role_notes: tuple[str, ...]
    ai_companies: set[str]
    world_government_company: str | None
    configured_rivals: set[str]
    active_companies: set[str]
    included_companies: set[str] | None
    meta: dict[str, str]
    current_time: datetime | None
    companies: list[dict[str, Any]]
    object_names: dict[int, str]
    object_types: dict[int, str]
    buildables: dict[str, str]
    resources: dict[str, str]
    transport_capacities: dict[str, dict[str, object]]
    technology_reference: TechReferenceCatalog
    mission_facts: list[MissionFact]
    cargo_facts: list[CargoFact]
    craft_facts: list[CraftFact]
    object_facts: dict[int, ObjectFact]
    resource_stock_facts: list[ResourceStockFact]
    known_resource_deposit_facts: list[KnownResourceDepositFact]
    tech_unlock_facts: list[TechUnlockFact]
    tech_modifier_facts: list[TechModifierFact]
    cargo_flight_metrics: list[CargoFlightMetric]
    route_metrics: list[RouteMetric]
    body_metrics: list[BodyMetric]
    crew_metrics: list[CrewMetric]
    population_readiness_metrics: list[PopulationReadinessMetric]
    population_destination_metrics: list[PopulationDestinationMetric]
    population_flight_metrics: list[PopulationFlightMetric]
    population_place_metrics: list[PopulationPlaceMetric]
    production_balance_metrics: list[ProductionBalanceMetric]
    return_fuel_metrics: list[ReturnFuelMetric]
    attention_rows: list[AttentionRow]
    fleet_rows: list[FleetRow]


@dataclass(frozen=True)
class CompanyRoles:
    player_company: str | None
    player_company_source: str
    player_company_authoritative: bool
    role_notes: tuple[str, ...]
    ai_companies: set[str]
    world_government_company: str | None
    configured_rivals: set[str]
    default_companies: set[str]
    expanded_companies: set[str]


@dataclass(frozen=True)
class StartConfigRoles:
    player_company: str | None
    configured_rivals: set[str]
    source: str
    authoritative: bool
    notes: tuple[str, ...]


def company_ids_from_save(save: dict[str, Any]) -> set[str]:
    companies = [company for company in list_content(save.get("companyDataSave")) if isinstance(company, dict)]
    return {company for row in companies if (company := str(id_value(row.get("companyID"), "")))}


def player_and_rivals_from_info(slot: SaveSlot | None) -> StartConfigRoles:
    if slot is None or slot.info_path is None:
        return StartConfigRoles(
            player_company=None,
            configured_rivals=set(),
            source="missing .info.gz sidecar",
            authoritative=False,
            notes=("The game stores the active player in the paired .info.gz sidecar, not in the save filename.",),
        )
    try:
        info = parse_save_file(slot.info_path)
    except (OSError, SaveParseError, ValueError) as exc:
        return StartConfigRoles(
            player_company=None,
            configured_rivals=set(),
            source="unreadable .info.gz sidecar",
            authoritative=False,
            notes=(f"Could not parse {slot.info_path.name}: {exc}",),
        )
    config = info.get("startGameConfiguration") if isinstance(info, dict) else None
    if not isinstance(config, dict):
        return StartConfigRoles(
            player_company=None,
            configured_rivals=set(),
            source="missing startGameConfiguration",
            authoritative=False,
            notes=(f"{slot.info_path.name} does not expose startGameConfiguration.",),
        )

    player = game_key(config.get("Company")) or None
    rivals = {company for item in list_content(config.get("enabledRivalCorporations")) if (company := game_key(item))}
    if not player:
        return StartConfigRoles(
            player_company=None,
            configured_rivals=rivals,
            source="missing startGameConfiguration.Company",
            authoritative=False,
            notes=(f"{slot.info_path.name} has startGameConfiguration but no Company field.",),
        )

    return StartConfigRoles(
        player_company=player,
        configured_rivals=rivals,
        source="SaveInfo.startGameConfiguration.Company",
        authoritative=True,
        notes=(),
    )


def ai_companies_from_save(save: dict[str, Any]) -> set[str]:
    ai_companies: set[str] = set()
    for row in list_content(save.get("companyAISave")):
        if not isinstance(row, dict):
            continue
        company = game_key(row.get("IDCompany") or row.get("companyID") or row.get("companyId"))
        if company:
            ai_companies.add(company)
    return ai_companies


def company_activity_scores(save: dict[str, Any]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for row in list_content(save.get("companyDataSave")):
        if not isinstance(row, dict):
            continue
        company = str(id_value(row.get("companyID"), ""))
        if not company:
            continue
        craft_count = len(list_content(row.get("spacecrafts")))
        mission_count = len(list_content(row.get("listMission")))
        cycle_count = len(list_content(row.get("listMissionCyclical")))
        hull_count = len(list_content(row.get("hullList")))
        scores[company] = mission_count * 100 + cycle_count * 100 + craft_count * 2 + hull_count
    return scores


def infer_player_company(save: dict[str, Any], ai_companies: set[str], world_government: str | None) -> tuple[str | None, str]:
    companies = company_ids_from_save(save)
    excluded = set(ai_companies)
    if world_government:
        excluded.add(world_government)
    candidates = companies - excluded
    if not candidates:
        return None, "unknown"
    if len(candidates) == 1:
        return next(iter(candidates)), "inferred from non-AI company list"

    scores = company_activity_scores(save)
    ranked = sorted(
        ((scores.get(company, 0), company) for company in candidates),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    if ranked and ranked[0][0] > 0 and (len(ranked) == 1 or ranked[0][0] > ranked[1][0]):
        return ranked[0][1], "inferred from non-AI company activity"
    return None, "unknown"


def company_roles(slot: SaveSlot | None, save: dict[str, Any]) -> CompanyRoles:
    company_ids = company_ids_from_save(save)
    info_roles = player_and_rivals_from_info(slot)
    ai_companies = ai_companies_from_save(save)
    world_government = "WorldGovernment" if "WorldGovernment" in company_ids or "WorldGovernment" in ai_companies else None
    non_ai_candidates = company_ids - ai_companies - ({world_government} if world_government else set())
    role_notes = list(info_roles.notes)

    player_company = info_roles.player_company
    player_source = info_roles.source
    player_authoritative = info_roles.authoritative
    if not player_company:
        player_company, player_source = infer_player_company(save, ai_companies, world_government)
        player_authoritative = False
        if player_company:
            role_notes.append("Player company is inferred from the main .json.gz because the authoritative .info.gz path was not usable.")

    if player_company and company_ids and player_company not in company_ids:
        role_notes.append(f"Authoritative player {player_company} was not present in companyDataSave; default scope is empty instead of widening to all companies.")

    if player_company:
        default_companies = {player_company} if player_company in company_ids else set()
    else:
        default_companies = non_ai_candidates
        if default_companies:
            role_notes.append("Player company is uncertain; default scope is limited to non-AI/non-WG candidates.")

    expanded_companies = set(default_companies) | ai_companies | info_roles.configured_rivals
    if world_government:
        expanded_companies.add(world_government)
    expanded_companies = {company for company in expanded_companies if company in company_ids}

    return CompanyRoles(
        player_company=player_company,
        player_company_source=player_source,
        player_company_authoritative=player_authoritative,
        role_notes=tuple(role_notes),
        ai_companies={company for company in ai_companies if company in company_ids},
        world_government_company=world_government,
        configured_rivals=info_roles.configured_rivals,
        default_companies={company for company in default_companies if company in company_ids},
        expanded_companies=expanded_companies,
    )


def fleet_rows_from_craft_facts(craft_facts: list[CraftFact]) -> list[FleetRow]:
    return [
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


def analyze_save(slot: SaveSlot, repo_root: Path, *, include_ai_and_wg: bool = False) -> SaveAnalysis:
    save = parse_save_file(slot.json_path)
    roles = company_roles(slot, save)
    included_companies = roles.expanded_companies if include_ai_and_wg else roles.default_companies
    active_companies = set(company_ids_from_save(save) if included_companies is None else included_companies)

    object_names, object_types = build_object_metadata(save, repo_root)
    buildables, resources = load_reference_maps(repo_root)
    transport_capacities = load_transport_capacities(repo_root)
    technology_reference = load_technology_reference_catalog(repo_root)
    current_time = extract_datetime(save.get("currentTime"))
    companies = [company for company in list_content(save.get("companyDataSave")) if isinstance(company, dict)]
    tech_unlock_facts, tech_modifier_facts = build_tech_facts(companies, included_companies)

    mission_facts = build_mission_facts(companies, object_names, resources, buildables, current_time)
    if included_companies is not None:
        mission_facts = [mission for mission in mission_facts if mission.company in included_companies]

    cargo_facts = build_cargo_facts(
        companies,
        mission_facts,
        resources,
        buildables,
        set(transport_capacities),
    )
    if included_companies is not None:
        cargo_facts = [cargo for cargo in cargo_facts if cargo.company in included_companies]
    craft_facts = build_craft_facts(
        save,
        repo_root,
        mission_facts=mission_facts,
        included_companies=included_companies,
        technology_reference=technology_reference,
        tech_unlock_facts=tech_unlock_facts,
    )
    object_facts = build_object_facts(
        save,
        repo_root,
        mission_facts=mission_facts,
        included_companies=included_companies,
    )
    resource_stock_facts = build_resource_stock_facts(save, object_names, resources, included_companies)
    known_resource_deposit_facts = build_known_resource_deposit_facts(
        save,
        object_facts,
        object_names,
        resources,
        included_companies,
    )
    cargo_flight_metrics = build_cargo_flight_metrics(cargo_facts, mission_facts, craft_facts, object_facts)
    route_metrics = build_route_metrics(craft_facts, cargo_facts)
    body_metrics = build_body_metrics(object_facts, craft_facts, cargo_facts, mission_facts)
    crew_metrics = build_crew_metrics(
        cargo_facts,
        craft_facts,
        transport_capacities,
        current_time,
        technology_reference,
        tech_unlock_facts,
    )
    production_balance_metrics = build_production_balance_metrics(
        resource_stock_facts,
        object_facts,
        technology_reference,
        tech_unlock_facts,
    )
    population_readiness_metrics = build_population_readiness_metrics(
        save,
        repo_root,
        cargo_facts,
        mission_facts,
        resource_stock_facts,
        object_facts,
        included_companies,
        technology_reference,
        tech_unlock_facts,
    )
    population_destination_metrics = build_population_destination_metrics(
        population_readiness_metrics,
        mission_facts,
        object_facts,
    )
    population_flight_metrics = build_population_flight_metrics(
        crew_metrics,
        mission_facts,
        population_readiness_metrics,
        object_facts,
    )
    population_place_metrics = build_population_place_metrics(
        save,
        repo_root,
        included_companies,
        resource_stock_facts,
        population_readiness_metrics,
        object_facts,
    )
    return_fuel_metrics = build_return_fuel_metrics(
        craft_facts,
        mission_facts,
        cargo_facts,
        resource_stock_facts,
        object_facts,
        resources,
    )
    attention_rows = build_attention_rows(
        return_fuel_metrics,
        craft_facts=craft_facts,
        mission_facts=mission_facts,
        population_readiness_metrics=population_readiness_metrics,
        cargo_facts=cargo_facts,
        object_facts=object_facts,
        cargo_flight_metrics=cargo_flight_metrics,
        resource_stock_facts=resource_stock_facts,
        tech_unlock_facts=tech_unlock_facts,
        technology_reference=technology_reference,
        buildables=buildables,
        resources=resources,
        transport_capacities=transport_capacities,
        company_role_notes=roles.role_notes,
    )
    fleet_rows = fleet_rows_from_craft_facts(craft_facts)

    meta = {
        "save_version": str(save.get("saveVersion") or ""),
        "current_time": fmt_dt(current_time),
        "companies": str(len({row.company for row in fleet_rows})),
        "raw_companies": str(len(companies)),
        "craft_count": str(len(fleet_rows)),
        "player_company": roles.player_company or "",
        "player_company_source": roles.player_company_source,
        "player_company_confidence": "authoritative" if roles.player_company_authoritative else "inferred",
        "company_scope": "Player + AI/WG" if include_ai_and_wg else "Player",
        "attention_count": str(len(attention_rows)),
        "fuel_attention_count": str(sum(1 for row in attention_rows if row.category == "Fuel")),
        "capacity_attention_count": str(sum(1 for row in attention_rows if row.category == "Capacity")),
        "route_attention_count": str(sum(1 for row in attention_rows if row.category == "Route")),
        "population_attention_count": str(sum(1 for row in attention_rows if row.category == "Population")),
        "cargo_attention_count": str(sum(1 for row in attention_rows if row.category == "Cargo")),
        "technology_attention_count": str(sum(1 for row in attention_rows if row.category == "Technology")),
        "save_data_attention_count": str(sum(1 for row in attention_rows if row.category == "Save Data")),
        "tech_unlock_count": str(len(tech_unlock_facts)),
        "tech_modifier_count": str(len(tech_modifier_facts)),
        "tech_reference_count": str(len(technology_reference.rows)),
        "tech_reference_modifier_count": str(len(technology_reference.modifiers)),
        "known_resource_deposit_count": str(len(known_resource_deposit_facts)),
    }

    return SaveAnalysis(
        slot=slot,
        repo_root=repo_root,
        save=save,
        player_company=roles.player_company,
        player_company_source=roles.player_company_source,
        player_company_authoritative=roles.player_company_authoritative,
        company_role_notes=roles.role_notes,
        ai_companies=roles.ai_companies,
        world_government_company=roles.world_government_company,
        configured_rivals=roles.configured_rivals,
        active_companies=active_companies,
        included_companies=included_companies,
        meta=meta,
        current_time=current_time,
        companies=companies,
        object_names=object_names,
        object_types=object_types,
        buildables=buildables,
        resources=resources,
        transport_capacities=transport_capacities,
        technology_reference=technology_reference,
        mission_facts=mission_facts,
        cargo_facts=cargo_facts,
        craft_facts=craft_facts,
        object_facts=object_facts,
        resource_stock_facts=resource_stock_facts,
        known_resource_deposit_facts=known_resource_deposit_facts,
        tech_unlock_facts=tech_unlock_facts,
        tech_modifier_facts=tech_modifier_facts,
        cargo_flight_metrics=cargo_flight_metrics,
        route_metrics=route_metrics,
        body_metrics=body_metrics,
        crew_metrics=crew_metrics,
        population_readiness_metrics=population_readiness_metrics,
        population_destination_metrics=population_destination_metrics,
        population_flight_metrics=population_flight_metrics,
        population_place_metrics=population_place_metrics,
        production_balance_metrics=production_balance_metrics,
        return_fuel_metrics=return_fuel_metrics,
        attention_rows=attention_rows,
        fleet_rows=fleet_rows,
    )
