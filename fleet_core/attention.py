from __future__ import annotations

from .fact_model import AttentionRow, CargoFact, CraftFact, MissionFact, ObjectFact, PopulationReadinessMetric, ReturnFuelMetric

SEVERITY_RANK = {
    "Critical": 0,
    "Urgent": 1,
    "Warning": 2,
    "Monitor": 3,
    "Info": 4,
}

POPULATION_ALERT_STATUSES = {"Critical", "Urgent", "Warning"}
TRANSIT_CARGO_KINDS = {"resource", "module", "crew_module", "fuel", "unknown"}


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
    company_role_notes: tuple[str, ...] = (),
) -> list[AttentionRow]:
    rows = fuel_attention_rows(return_fuel_metrics)
    if craft_facts is not None and mission_facts is not None:
        rows.extend(capacity_attention_rows(craft_facts, mission_facts))
    if population_readiness_metrics is not None and mission_facts is not None:
        rows.extend(population_attention_rows(population_readiness_metrics, mission_facts))
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
