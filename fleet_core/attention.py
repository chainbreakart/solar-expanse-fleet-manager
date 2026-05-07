from __future__ import annotations

from .fact_model import (
    AttentionRow,
    CargoFact,
    CargoFlightMetric,
    CraftFact,
    MissionFact,
    ObjectFact,
    PopulationReadinessMetric,
    ResourceStockFact,
    ReturnFuelMetric,
    TechReferenceCatalog,
    TechReferenceModifier,
    TechUnlockFact,
)

SEVERITY_RANK = {
    "Critical": 0,
    "Urgent": 1,
    "Warning": 2,
    "Monitor": 3,
    "Info": 4,
}

POPULATION_ALERT_STATUSES = {"Critical", "Urgent", "Warning"}
TRANSIT_CARGO_KINDS = {"resource", "module", "crew_module", "fuel", "unknown"}
CARGO_ATTENTION_STATUSES = {"En route", "Cyclical", "Planned"}


def tons(value: float | None) -> str:
    if value is None:
        return "unknown"
    if abs(value) >= 1000:
        return f"{value:,.0f}t"
    if abs(value - round(value)) < 0.005:
        return f"{value:.0f}t"
    return f"{value:.1f}t"


def fuel_attention_severity(warning: str) -> str:
    if warning == "Return fuel shortfall":
        return "Critical"
    if warning == "Return fuel needs surface lift":
        return "Warning"
    return "Info"


def fuel_attention_title(warning: str) -> str:
    if warning == "Return fuel shortfall":
        return "Return fuel shortfall"
    if warning == "Return fuel needs surface lift":
        return "Return fuel needs surface lift"
    return warning or "Return fuel note"


def fuel_attention_message(metric: ReturnFuelMetric) -> str:
    requirement = tons(metric.estimated_return_requirement)
    immediate_margin = tons(metric.immediate_return_margin)
    if metric.warning == "Return fuel needs surface lift":
        lift = tons(metric.lift_needed_surface_fuel)
        surface = metric.surface_stock_object or metric.destination
        return (
            f"{metric.craft_name} may have enough {metric.fuel_type} after lifting {lift} "
            f"from {surface}; immediate return margin is {immediate_margin}."
        )
    return (
        f"{metric.craft_name} is below the estimated {requirement} return-fuel need at "
        f"{metric.destination}; immediate margin is {immediate_margin}."
    )


def fuel_attention_details(metric: ReturnFuelMetric) -> tuple[str, ...]:
    immediate_object = metric.immediate_stock_object or metric.destination
    surface_object = metric.surface_stock_object or "no linked surface stock"
    return (
        f"Return need: {tons(metric.estimated_return_requirement)} "
        f"({metric.return_requirement_confidence}; {metric.requirement_basis})",
        f"Arrival fuel: {tons(metric.expected_onboard_fuel_at_arrival)} "
        f"({metric.expected_onboard_fuel_basis})",
        f"Compatible fuel cargo: {tons(metric.compatible_fuel_cargo)}",
        f"Destination immediate stock: {tons(metric.destination_immediate_stock)} at {immediate_object}",
        f"Destination surface stock: {tons(metric.destination_surface_stock)} at {surface_object}",
        f"Lift needed from surface: {tons(metric.lift_needed_surface_fuel)}",
        f"Immediate margin: {tons(metric.immediate_return_margin)}",
        f"After surface lift: {tons(metric.deferred_return_margin)}",
    )


def fuel_attention_rows(return_fuel_metrics: list[ReturnFuelMetric]) -> list[AttentionRow]:
    rows: list[AttentionRow] = []
    for metric in return_fuel_metrics:
        if not metric.warning:
            continue
        rows.append(
            AttentionRow(
                attention_key=f"fuel:{metric.return_key}",
                severity=fuel_attention_severity(metric.warning),
                category="Fuel",
                source="ReturnFuelMetric.warning",
                company=metric.company,
                title=fuel_attention_title(metric.warning),
                message=fuel_attention_message(metric),
                route=metric.route,
                body=metric.destination,
                craft_id=metric.craft_id,
                craft_name=metric.craft_name,
                mission_key=metric.return_key,
                drilldown="Return Fuel Board",
                event_date=metric.arrival or metric.departure,
                details=fuel_attention_details(metric),
            )
        )
    return rows


def route_destination(route: str) -> str:
    if "->" in route:
        return route.rsplit("->", 1)[-1].strip()
    if "<->" in route:
        return route.rsplit("<->", 1)[-1].strip()
    return route


def craft_manifest(crafts: list[CraftFact]) -> str:
    names = [f"{craft.craft_name} ({tons(craft.cargo_capacity)})" for craft in crafts[:6]]
    if len(crafts) > 6:
        names.append(f"+ {len(crafts) - 6} more")
    return "; ".join(names)


def capacity_attention_rows(craft_facts: list[CraftFact], mission_facts: list[MissionFact]) -> list[AttentionRow]:
    mission_by_key = {mission.mission_key: mission for mission in mission_facts}
    craft_by_assignment: dict[tuple[str, str], list[CraftFact]] = {}
    for craft in craft_facts:
        if not craft.has_active_assignment or not craft.active_assignment_key:
            continue
        if craft.status in {"Arrived", "Canceled"}:
            continue
        craft_by_assignment.setdefault((craft.company, craft.active_assignment_key), []).append(craft)

    rows: list[AttentionRow] = []
    for (company, assignment_key), crafts in craft_by_assignment.items():
        mission = mission_by_key.get(assignment_key)
        if not mission or mission.status in {"Arrived", "Canceled"}:
            continue
        if not crafts:
            continue
        if any(craft.capacity_source != "save_hull" for craft in crafts):
            continue
        if any(craft.capacity_semantics != "normal" for craft in crafts):
            continue
        if any(craft.cargo_capacity is None for craft in crafts):
            continue

        cargo_capacity = sum(float(craft.cargo_capacity or 0.0) for craft in crafts)
        cargo_mass = mission.cargo_mass
        if cargo_mass <= cargo_capacity + 0.01:
            continue

        overage = cargo_mass - cargo_capacity
        route = mission.route or crafts[0].route
        rows.append(
            AttentionRow(
                attention_key=f"capacity:{company}:{assignment_key}",
                severity="Monitor",
                category="Capacity",
                source="CraftFact.capacity_metrics",
                company=company,
                title="Live hull capacity mismatch",
                message=(
                    f"{mission.mission_type.title()} payload is {tons(cargo_mass)} against "
                    f"{tons(cargo_capacity)} summed live hull cargo capacity; over by {tons(overage)}."
                ),
                route=route,
                body=route_destination(route),
                craft_id=crafts[0].craft_id if len(crafts) == 1 else None,
                craft_name=crafts[0].craft_name if len(crafts) == 1 else f"{len(crafts)} assigned craft",
                mission_key=assignment_key,
                drilldown="Fleet Board",
                event_date=mission.arrival or mission.departure,
                details=(
                    "Diagnostic only: the in-game mission planner should normally block over-capacity launches.",
                    "Only emitted when every assigned craft uses live save hull capacity, not static reference capacity.",
                    f"Mission cargo mass: {tons(cargo_mass)}",
                    f"Summed live hull cargo capacity: {tons(cargo_capacity)}",
                    f"Overage: {tons(overage)}",
                    f"Assigned craft: {craft_manifest(crafts)}",
                    f"Mission status: {mission.status}",
                ),
            )
        )
    return rows


def numeric_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def cyclical_halt_reasons(mission: MissionFact) -> tuple[str, ...]:
    if mission.mission_type != "cyclical":
        return ()
    reasons: list[str] = []
    if mission.status == "Cyclical paused":
        reasons.append("Pause flag is set in the save.")
    ends = numeric_value(mission.raw.get("Ends"))
    count_mission = numeric_value(mission.raw.get("CountMission"))
    count_max = numeric_value(mission.raw.get("CountMax"))
    if ends == 1 and count_max is not None and count_max > 0 and count_mission is not None and count_mission >= count_max:
        reasons.append(f"Trip count reached the saved limit ({count_mission:.0f}/{count_max:.0f}).")
    return tuple(reasons)


def route_attention_rows(mission_facts: list[MissionFact]) -> list[AttentionRow]:
    rows: list[AttentionRow] = []
    for mission in mission_facts:
        halt_reasons = cyclical_halt_reasons(mission)
        if halt_reasons:
            rows.append(
                AttentionRow(
                    attention_key=f"route:cyclical-halt:{mission.company}:{mission.mission_key}",
                    severity="Warning" if mission.status == "Cyclical paused" else "Monitor",
                    category="Route",
                    source="MissionFact.raw",
                    company=mission.company,
                    title="Cyclical route halted",
                    message=f"{mission.route} is not currently cycling; saved route settings indicate a deterministic halt.",
                    route=mission.route,
                    body=route_destination(mission.route),
                    craft_id=mission.craft_ids[0] if len(mission.craft_ids) == 1 else None,
                    craft_name=f"{len(mission.craft_ids)} assigned craft" if len(mission.craft_ids) > 1 else "",
                    mission_key=mission.mission_key,
                    drilldown="Route Board",
                    event_date="",
                    details=(
                        *halt_reasons,
                        f"Status: {mission.status}",
                        f"Transfer/cargo settings: {mission.transfer or 'not exposed'}",
                    ),
                )
            )
            continue
    return rows


def population_attention_title(metric: PopulationReadinessMetric) -> str:
    if metric.housing_gap > 0 and metric.completed_housing + metric.queued_housing <= 0:
        return "Population housing unavailable"
    if metric.housing_gap > 0:
        return "Population housing shortfall"
    if metric.projected_population > metric.completed_housing and metric.queued_housing > 0:
        return "Population depends on build queue"
    if metric.projected_supply_net_per_day < 0:
        return "Population supply runway"
    return "Population readiness"


def population_attention_rows(
    population_readiness_metrics: list[PopulationReadinessMetric],
    mission_facts: list[MissionFact],
) -> list[AttentionRow]:
    mission_by_key = {mission.mission_key: mission for mission in mission_facts}
    grouped: dict[tuple[str, int | None], list[PopulationReadinessMetric]] = {}
    for metric in population_readiness_metrics:
        if metric.status not in POPULATION_ALERT_STATUSES:
            continue
        grouped.setdefault((metric.company, metric.destination_id), []).append(metric)

    rows: list[AttentionRow] = []
    for (company, destination_id), metrics in grouped.items():
        metrics.sort(
            key=lambda metric: (
                SEVERITY_RANK.get(metric.status, 99),
                mission_by_key.get(metric.mission_key).arrival if mission_by_key.get(metric.mission_key) else "9999",
                metric.mission_key,
            )
        )
        metric = metrics[0]
        missions = [mission_by_key.get(item.mission_key) for item in metrics]
        missions = [mission for mission in missions if mission is not None]
        event_date = min((mission.arrival or mission.departure for mission in missions if mission.arrival or mission.departure), default="")
        route = missions[0].route if len(missions) == 1 and missions[0] else f"{len(metrics)} inbound population missions"
        affected = "; ".join(
            f"{mission.route} ({mission.arrival or mission.departure or 'no date'})" for mission in missions[:5]
        )
        if len(missions) > 5:
            affected = f"{affected}; + {len(missions) - 5} more"
        detail_lines = list(metric.details)
        if affected:
            detail_lines.append(f"Affected inbound missions: {affected}")
        detail_lines.append("No destination population-need-without-inbound alert is emitted until the demand model exists.")

        rows.append(
            AttentionRow(
                attention_key=f"population:{company}:{destination_id}",
                severity=metric.status,
                category="Population",
                source="PopulationReadinessMetric.status",
                company=company,
                title=population_attention_title(metric),
                message=metric.message,
                route=route,
                body=metric.destination,
                craft_id=None,
                craft_name="",
                mission_key=metric.mission_key,
                drilldown="People Movement",
                event_date=event_date,
                details=tuple(detail_lines),
            )
        )
    return rows


def cargo_item_summary(items: dict[str, float], *, limit: int = 5) -> str:
    pieces = [f"{name} {tons(value)}" for name, value in sorted(items.items(), key=lambda item: (-item[1], item[0]))[:limit]]
    if len(items) > limit:
        pieces.append(f"+ {len(items) - limit} more")
    return "; ".join(pieces)


def cargo_flight_summary(flights: list[CargoFlightMetric], *, limit: int = 5) -> str:
    pieces = [
        f"{flight.mission_id or flight.mission_key}: {flight.route or flight.destination or 'unknown route'}"
        f" ({flight.arrival or flight.departure or 'no date'})"
        for flight in flights[:limit]
    ]
    if len(flights) > limit:
        pieces.append(f"+ {len(flights) - limit} more")
    return "; ".join(pieces)


def cargo_attention_rows(
    cargo_flight_metrics: list[CargoFlightMetric],
    resource_stock_facts: list[ResourceStockFact] | None = None,
) -> list[AttentionRow]:
    stock_keys = {
        (fact.company, fact.object_id, fact.resource_key)
        for fact in resource_stock_facts or []
        if fact.resource_key
    }
    missing_receipts: dict[tuple[str, int, str], dict[str, object]] = {}
    missing_destinations: dict[str, list[CargoFlightMetric]] = {}
    undated_arrivals: dict[str, list[CargoFlightMetric]] = {}

    for flight in cargo_flight_metrics:
        if flight.status not in CARGO_ATTENTION_STATUSES or flight.total_tons <= 0:
            continue
        if flight.target_id is None:
            missing_destinations.setdefault(flight.company, []).append(flight)
            continue
        if flight.arrival_dt is None and flight.status in {"En route", "Planned"}:
            undated_arrivals.setdefault(flight.company, []).append(flight)

        missing_items: dict[str, float] = {}
        for detail in flight.details:
            if not detail.resource_key or detail.mass <= 0:
                continue
            if (flight.company, flight.target_id, detail.resource_key) in stock_keys:
                continue
            missing_items[detail.name] = missing_items.get(detail.name, 0.0) + detail.mass
        if not missing_items:
            continue
        key = (flight.company, flight.target_id, flight.destination)
        group = missing_receipts.setdefault(
            key,
            {
                "flights": [],
                "items": {},
                "support_tons": 0.0,
                "event_date": "",
            },
        )
        group["flights"].append(flight)
        group_items = group["items"]
        assert isinstance(group_items, dict)
        for item_name, mass in missing_items.items():
            group_items[item_name] = float(group_items.get(item_name, 0.0)) + mass
        group["support_tons"] = float(group["support_tons"]) + flight.colonization_support_tons
        if not group["event_date"] or (flight.arrival and flight.arrival < group["event_date"]):
            group["event_date"] = flight.arrival

    rows: list[AttentionRow] = []
    for (company, target_id, destination), group in missing_receipts.items():
        flights = sorted(group["flights"], key=lambda flight: (flight.arrival or "9999", flight.mission_id, flight.flight_key))
        items = group["items"]
        assert isinstance(items, dict)
        support_tons = float(group["support_tons"])
        severity = "Warning" if support_tons > 0 else "Monitor"
        rows.append(
            AttentionRow(
                attention_key=f"cargo:receipt-evidence:{company}:{target_id}",
                severity=severity,
                category="Cargo",
                source="CargoFlightMetric.destination_receipt_evidence",
                company=company,
                title="Cargo receipt lacks local evidence",
                message=(
                    f"{destination} has inbound cargo without matching local stock/flow rows "
                    f"for {cargo_item_summary(items, limit=3)}."
                ),
                route=f"{len(flights)} inbound cargo flight(s)" if len(flights) != 1 else flights[0].route,
                body=destination,
                craft_id=flights[0].craft_ids[0] if len(flights) == 1 and len(flights[0].craft_ids) == 1 else None,
                craft_name=flights[0].craft_names[0] if len(flights) == 1 and len(flights[0].craft_names) == 1 else "",
                mission_key=flights[0].mission_key if len(flights) == 1 else "",
                drilldown="Cargo",
                event_date=str(group["event_date"]),
                details=(
                    f"Missing local receipt evidence: {cargo_item_summary(items)}",
                    f"Colony-support cargo in affected flights: {tons(support_tons)}",
                    f"Affected cargo flights: {cargo_flight_summary(flights)}",
                    "Evidence expectation: resource/fuel receipts should join to destination-local stock/flow/runway rows when the save exposes that production data.",
                ),
            )
        )

    for company, flights in missing_destinations.items():
        flights = sorted(flights, key=lambda flight: (flight.arrival or "9999", flight.mission_id, flight.flight_key))
        rows.append(
            AttentionRow(
                attention_key=f"cargo:destination-missing:{company}",
                severity="Warning",
                category="Cargo",
                source="CargoFlightMetric.target_id",
                company=company,
                title="Cargo destination missing",
                message=f"{len(flights)} active/planned cargo flight(s) have no parsed destination object.",
                route=f"{len(flights)} cargo flight(s)",
                body="",
                craft_id=None,
                craft_name="",
                mission_key=flights[0].mission_key if len(flights) == 1 else "",
                drilldown="Cargo",
                event_date=flights[0].arrival or flights[0].departure,
                details=(f"Affected cargo flights: {cargo_flight_summary(flights)}",),
            )
        )

    for company, flights in undated_arrivals.items():
        flights = sorted(flights, key=lambda flight: (flight.departure or "9999", flight.mission_id, flight.flight_key))
        rows.append(
            AttentionRow(
                attention_key=f"cargo:arrival-date-missing:{company}",
                severity="Monitor",
                category="Cargo",
                source="CargoFlightMetric.arrival_dt",
                company=company,
                title="Cargo arrival date missing",
                message=f"{len(flights)} active/planned cargo flight(s) have cargo but no trusted arrival date.",
                route=f"{len(flights)} cargo flight(s)",
                body="",
                craft_id=None,
                craft_name="",
                mission_key=flights[0].mission_key if len(flights) == 1 else "",
                drilldown="Cargo",
                event_date=flights[0].departure,
                details=(f"Affected cargo flights: {cargo_flight_summary(flights)}",),
            )
        )

    return rows


def technology_target_valid(
    modifier: TechReferenceModifier,
    *,
    known_buildables: set[str],
    known_modules: set[str],
    known_resources: set[str],
    known_spacecraft: set[str],
) -> bool:
    if modifier.target_key == "All":
        return True
    if modifier.target_type == "spacecraft":
        return modifier.target_key in known_spacecraft
    if modifier.target_type == "facility":
        return modifier.target_key in known_buildables
    if modifier.target_type == "module":
        return modifier.target_key in known_modules
    if modifier.target_type == "resource":
        return modifier.target_key in known_resources
    if modifier.target_type in {"population", "ship"}:
        return modifier.target_key == "All"
    return False


def technology_reference_attention_rows(
    tech_unlock_facts: list[TechUnlockFact],
    technology_reference: TechReferenceCatalog | None,
    *,
    buildables: dict[str, str] | None = None,
    resources: dict[str, str] | None = None,
    transport_capacities: dict[str, dict[str, object]] | None = None,
) -> list[AttentionRow]:
    if technology_reference is None:
        return []

    rows: list[AttentionRow] = []
    unknown_unlocks = [
        fact
        for fact in tech_unlock_facts
        if fact.research_id and fact.research_id not in technology_reference.by_research_id
    ]
    if unknown_unlocks:
        first = sorted(unknown_unlocks, key=lambda fact: (fact.company, fact.research_id, fact.status))[0]
        rows.append(
            AttentionRow(
                attention_key="technology:unknown-research-ids",
                severity="Warning",
                category="Technology",
                source="TechUnlockFact.research_id",
                company=first.company,
                title="Unknown technology research IDs",
                message=(
                    f"{len(unknown_unlocks)} focused-save research row(s) have no Fleet Manager technology reference row."
                ),
                route="",
                body="",
                craft_id=None,
                craft_name="",
                mission_key="",
                drilldown="Technology",
                event_date="",
                details=tuple(
                    f"{fact.company}: {fact.research_id} ({fact.status}; {fact.source_path})"
                    for fact in sorted(unknown_unlocks, key=lambda item: (item.company, item.research_id, item.status))[:12]
                ),
            )
        )

    known_spacecraft = {
        spacecraft
        for row in technology_reference.rows
        for spacecraft in row.unlocked_spacecraft
    }
    known_buildables = set(buildables or {}) | {
        facility
        for row in technology_reference.rows
        for facility in row.unlocked_facilities
    }
    known_modules = set(transport_capacities or {}) | {
        module
        for row in technology_reference.rows
        for module in row.unlocked_modules
    }
    known_resources = set(resources or {}) | {
        resource
        for row in technology_reference.rows
        for resource in row.unlocked_resources
    }
    missing_targets = [
        modifier
        for modifier in technology_reference.modifiers
        if not technology_target_valid(
            modifier,
            known_buildables=known_buildables,
            known_modules=known_modules,
            known_resources=known_resources,
            known_spacecraft=known_spacecraft,
        )
    ]
    if missing_targets:
        first = sorted(missing_targets, key=lambda item: (item.research_id, item.target_type, item.target_key))[0]
        rows.append(
            AttentionRow(
                attention_key="technology:missing-reference-targets",
                severity="Warning",
                category="Technology",
                source="TechReferenceModifier.target_key",
                company="",
                title="Technology reference targets missing",
                message=f"{len(missing_targets)} technology reference modifier target(s) do not resolve to known game-data keys.",
                route="",
                body="",
                craft_id=None,
                craft_name="",
                mission_key="",
                drilldown="Technology",
                event_date="",
                details=tuple(
                    f"{modifier.research_id}: {modifier.modifier_type} -> {modifier.target_type}:{modifier.target_key} ({modifier.source})"
                    for modifier in sorted(missing_targets, key=lambda item: (item.research_id, item.target_type, item.target_key))[:12]
                )
                or (f"{first.research_id}: {first.target_type}:{first.target_key}",),
            )
        )

    return rows


def cargo_context(cargo: CargoFact) -> str:
    mission = f"mission {cargo.mission_id}" if cargo.mission_id else cargo.source_key
    name = cargo.display_name or cargo.cargo_kind or "cargo"
    return f"{mission}: {name} in {cargo.list_label}"


def cargo_anomaly_attention_rows(cargo_facts: list[CargoFact]) -> list[AttentionRow]:
    malformed: list[CargoFact] = []
    zero_mass: list[CargoFact] = []
    for cargo in cargo_facts:
        if cargo.source_type != "mission":
            continue
        if cargo.mission_status in {"Arrived", "Canceled"}:
            continue
        if cargo.cargo_kind == "unknown":
            malformed.append(cargo)
        if cargo.cargo_kind in TRANSIT_CARGO_KINDS and cargo.mass <= 0 and cargo.life_support <= 0 and cargo.people <= 0:
            zero_mass.append(cargo)

    rows: list[AttentionRow] = []
    if malformed:
        sample = malformed[0]
        rows.append(
            AttentionRow(
                attention_key="save-data:cargo:malformed",
                severity="Warning",
                category="Save Data",
                source="CargoFact.cargo_kind",
                company=sample.company,
                title="Malformed cargo rows",
                message=f"{len(malformed)} active/planned cargo row(s) could not be classified as a resource, module, crew module, or fuel.",
                route=sample.route,
                body=route_destination(sample.route),
                craft_id=sample.craft_ids[0] if len(sample.craft_ids) == 1 else None,
                craft_name="",
                mission_key=sample.mission_key,
                drilldown="Cargo",
                event_date=sample.arrival or sample.departure,
                details=tuple(cargo_context(cargo) for cargo in malformed[:10]),
            )
        )
    if zero_mass:
        sample = zero_mass[0]
        rows.append(
            AttentionRow(
                attention_key="save-data:cargo:zero-mass",
                severity="Monitor",
                category="Save Data",
                source="CargoFact.mass",
                company=sample.company,
                title="Suspicious zero-mass cargo rows",
                message=f"{len(zero_mass)} active/planned cargo row(s) have no mass, people, or life-support value.",
                route=sample.route,
                body=route_destination(sample.route),
                craft_id=sample.craft_ids[0] if len(sample.craft_ids) == 1 else None,
                craft_name="",
                mission_key=sample.mission_key,
                drilldown="Cargo",
                event_date=sample.arrival or sample.departure,
                details=tuple(cargo_context(cargo) for cargo in zero_mass[:10]),
            )
        )
    return rows


def object_anomaly_attention_rows(
    object_facts: dict[int, ObjectFact],
    mission_facts: list[MissionFact],
    craft_facts: list[CraftFact],
) -> list[AttentionRow]:
    referenced: dict[int, list[str]] = {}
    for mission in mission_facts:
        for label, object_id in (("start", mission.start_id), ("target", mission.target_id)):
            if object_id is not None:
                referenced.setdefault(object_id, []).append(f"{mission.mission_id or mission.mission_key} {label}: {mission.route}")
    for craft in craft_facts:
        for label, object_id in (("current", craft.current_object_id), ("true", craft.true_object_id)):
            if object_id is not None:
                referenced.setdefault(object_id, []).append(f"{craft.craft_name} {label} object")

    unknowns = [
        (object_id, object_facts[object_id], references)
        for object_id, references in referenced.items()
        if (object_id in object_facts and object_facts[object_id].object_type == "Unknown" and object_facts[object_id].raw is None)
    ]
    if not unknowns:
        return []

    object_id, fact, references = sorted(unknowns, key=lambda item: item[0])[0]
    return [
        AttentionRow(
            attention_key="save-data:object:unknown",
            severity="Monitor",
            category="Save Data",
            source="ObjectFact.object_type",
            company=", ".join(fact.owner_companies),
            title="Unknown object references",
            message=f"{len(unknowns)} referenced object ID(s) have no known type/name metadata.",
            route="",
            body=fact.label,
            craft_id=None,
            craft_name="",
            mission_key="",
            drilldown="Body Board",
            event_date="",
            details=tuple(
                f"Object {item_id}: " + "; ".join(item_refs[:3])
                for item_id, _item_fact, item_refs in sorted(unknowns, key=lambda item: item[0])[:10]
            ) or tuple(references),
        )
    ]


def parser_note_attention_rows(company_role_notes: tuple[str, ...]) -> list[AttentionRow]:
    if not company_role_notes:
        return []
    return [
        AttentionRow(
            attention_key="save-data:parser:scope-notes",
            severity="Info",
            category="Save Data",
            source="SaveAnalysis.company_role_notes",
            company="",
            title="Save parser scope note",
            message="The selected save needed non-authoritative or fallback company-scope handling.",
            route="",
            body="",
            craft_id=None,
            craft_name="",
            mission_key="",
            drilldown="Save Selector",
            event_date="",
            details=company_role_notes,
        )
    ]


def save_data_attention_rows(
    cargo_facts: list[CargoFact] | None = None,
    object_facts: dict[int, ObjectFact] | None = None,
    mission_facts: list[MissionFact] | None = None,
    craft_facts: list[CraftFact] | None = None,
    company_role_notes: tuple[str, ...] = (),
) -> list[AttentionRow]:
    rows: list[AttentionRow] = []
    if cargo_facts is not None:
        rows.extend(cargo_anomaly_attention_rows(cargo_facts))
    if object_facts is not None and mission_facts is not None and craft_facts is not None:
        rows.extend(object_anomaly_attention_rows(object_facts, mission_facts, craft_facts))
    rows.extend(parser_note_attention_rows(company_role_notes))
    return rows


def build_attention_rows(
    return_fuel_metrics: list[ReturnFuelMetric],
    craft_facts: list[CraftFact] | None = None,
    mission_facts: list[MissionFact] | None = None,
    population_readiness_metrics: list[PopulationReadinessMetric] | None = None,
    cargo_facts: list[CargoFact] | None = None,
    object_facts: dict[int, ObjectFact] | None = None,
    cargo_flight_metrics: list[CargoFlightMetric] | None = None,
    resource_stock_facts: list[ResourceStockFact] | None = None,
    tech_unlock_facts: list[TechUnlockFact] | None = None,
    technology_reference: TechReferenceCatalog | None = None,
    buildables: dict[str, str] | None = None,
    resources: dict[str, str] | None = None,
    transport_capacities: dict[str, dict[str, object]] | None = None,
    company_role_notes: tuple[str, ...] = (),
) -> list[AttentionRow]:
    rows = fuel_attention_rows(return_fuel_metrics)
    if craft_facts is not None and mission_facts is not None:
        rows.extend(capacity_attention_rows(craft_facts, mission_facts))
    if mission_facts is not None:
        rows.extend(route_attention_rows(mission_facts))
    if population_readiness_metrics is not None and mission_facts is not None:
        rows.extend(population_attention_rows(population_readiness_metrics, mission_facts))
    if cargo_flight_metrics is not None:
        rows.extend(cargo_attention_rows(cargo_flight_metrics, resource_stock_facts))
    if tech_unlock_facts is not None and technology_reference is not None:
        rows.extend(
            technology_reference_attention_rows(
                tech_unlock_facts,
                technology_reference,
                buildables=buildables,
                resources=resources,
                transport_capacities=transport_capacities,
            )
        )
    rows.extend(save_data_attention_rows(cargo_facts, object_facts, mission_facts, craft_facts, company_role_notes))
    return sorted(
        rows,
        key=lambda row: (
            SEVERITY_RANK.get(row.severity, 99),
            row.event_date or "9999",
            row.company,
            row.category,
            row.craft_name,
            row.attention_key,
        ),
    )
