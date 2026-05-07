from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
from urllib.parse import urlencode

from nicegui import ui

from fleet_core.analysis import SaveAnalysis
from fleet_core.fact_model import CraftFact
from fleet_core.normalizer_utils import ROUTE_ACTIVE_STATUSES, ROUTE_PLANNED_STATUSES, fmt_num
from fleet_modules.shared import data_tab_link, fleet_link

FILTER_ALL_COMPANIES = "All companies"
FILTER_ALL_STATUSES = "All statuses"
FILTER_ALL_LOCATIONS = "All locations"
FILTER_ALL_TYPES = "All hulls/types"
FILTER_ALL_STATES = "All fleet states"
FILTER_ALL_CARGO = "All cargo states"
FILTER_CARGO_PRESENT = "Cargo/fuel present"
FILTER_CARGO_EMPTY = "No cargo/fuel"
FILTER_ALL_PEOPLE = "All people states"
FILTER_PEOPLE_CONTEXT = "Any people context"
FILTER_PEOPLE_ABOARD = "People aboard"
FILTER_EMPTY_SEATS = "Empty seats"
FILTER_NO_PEOPLE_CONTEXT = "No people context"
FILTER_ALL_WARNINGS = "All warning states"
FILTER_WARNINGS = "Warnings/attention"
FILTER_CLEAN = "Clean"
FILTER_ALL_ASSIGNMENTS = "All assignment states"
FILTER_ASSIGNED = "Assigned"
FILTER_UNASSIGNED = "Unassigned/idle"
FILTER_ACTIVE_ASSIGNMENT = "Active assignment"
FILTER_PLANNED_ASSIGNMENT = "Planned assignment"
SORT_DEFAULT = "Default"
SORT_CRAFT = "Craft"
SORT_STATE = "State"
SORT_LOCATION = "Location"
SORT_WARNINGS = "Warnings first"
SORT_ASSIGNMENT = "Assignment"
SORT_TYPE = "Hull / type"


def _is_loaded(craft: CraftFact) -> bool:
    return craft.cargo_mass > 0 or craft.fuel_mass > 0 or bool(craft.cargo and craft.cargo != "-")


def _status_bucket(craft: CraftFact) -> str:
    if craft.status in ROUTE_ACTIVE_STATUSES:
        return "Active"
    if craft.status in ROUTE_PLANNED_STATUSES:
        return "Planned"
    if craft.status == "Idle" or not craft.has_active_assignment:
        return "Idle"
    return craft.status or "Unknown"


def _short_text(value: str, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _cargo_summary_for_craft(analysis: SaveAnalysis, craft: CraftFact) -> str:
    summaries: list[str] = []
    for flight in analysis.cargo_flight_metrics:
        if craft.craft_id not in flight.craft_ids:
            continue
        if flight.total_tons:
            summaries.append(f"{fmt_num(flight.total_tons)}t cargo")
        if flight.colonization_support_tons:
            summaries.append(f"{fmt_num(flight.colonization_support_tons)}t colony support")
        if flight.fuel_tons:
            summaries.append(f"{fmt_num(flight.fuel_tons)}t fuel cargo")
        if flight.cargo_totals:
            top = "; ".join(f"{name} {fmt_num(tons)}t" for name, tons in flight.cargo_totals[:3])
            summaries.append(top)
    if summaries:
        return "; ".join(dict.fromkeys(summaries))
    if craft.cargo_mass:
        return f"{fmt_num(craft.cargo_mass)}t cargo"
    return _short_text(craft.cargo)


def _people_summary_for_craft(analysis: SaveAnalysis, craft: CraftFact) -> tuple[str, int, int]:
    crew_rows = [row for row in analysis.crew_metrics if row.craft_id == craft.craft_id]
    people = sum(row.people for row in crew_rows)
    empty_seats = sum(row.empty_seats or 0 for row in crew_rows)
    if people or empty_seats:
        parts = []
        if people:
            parts.append(f"{fmt_num(people)} people")
        if empty_seats:
            parts.append(f"{fmt_num(empty_seats)} empty seats")
        return "; ".join(parts), people, empty_seats
    return "-", 0, 0


def _return_fuel_summary_for_craft(analysis: SaveAnalysis, craft: CraftFact) -> tuple[str, str]:
    rows = [row for row in analysis.return_fuel_metrics if row.craft_id == craft.craft_id]
    warnings = [row.warning for row in rows if row.warning]
    if warnings:
        return warnings[0], "Warning"
    if rows:
        return "return fuel checked", "Checked"
    return _short_text(craft.fuel_plan), "Unknown"


def _attention_summary_for_craft(analysis: SaveAnalysis, craft: CraftFact) -> tuple[int, str]:
    rows = [row for row in analysis.attention_rows if row.craft_id == craft.craft_id]
    if not rows:
        return 0, ""
    severities = Counter(row.severity for row in rows)
    critical = severities.get("Critical", 0)
    warning = severities.get("Warning", 0)
    if critical:
        label = f"{critical} critical"
    elif warning:
        label = f"{warning} warning"
    else:
        label = f"{len(rows)} attention"
    return len(rows), label


def fleet_control_rows(analysis: SaveAnalysis) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for craft in sorted(analysis.craft_facts, key=lambda row: (row.company, row.craft_name, row.craft_id)):
        status_bucket = _status_bucket(craft)
        cargo_summary = _cargo_summary_for_craft(analysis, craft)
        people_summary, people_count, empty_seats = _people_summary_for_craft(analysis, craft)
        fuel_summary, fuel_state = _return_fuel_summary_for_craft(analysis, craft)
        attention_count, attention_summary = _attention_summary_for_craft(analysis, craft)
        mission_filter = craft.mission_id or craft.active_assignment_key
        route = _short_text(craft.route, "")
        rows.append(
            {
                "key": f"{craft.company}:{craft.craft_id}",
                "company": craft.company,
                "craft_id": craft.craft_id,
                "craft": craft.craft_name,
                "type": craft.spacecraft_type or craft.spacecraft_type_key or "-",
                "location": _short_text(craft.current_object),
                "location_id": craft.current_object_id or "",
                "status": craft.status or status_bucket,
                "bucket": status_bucket,
                "assignment": route or "-",
                "mission": mission_filter,
                "departure": _short_text(craft.departure),
                "arrival": _short_text(craft.arrival),
                "cargo": cargo_summary,
                "people": people_summary,
                "people_count": people_count,
                "empty_seats": empty_seats,
                "people_context": people_count > 0 or empty_seats > 0,
                "fuel": fuel_summary,
                "fuel_state": fuel_state,
                "capacity": _short_text(craft.capacity),
                "warnings": _short_text(craft.warnings, attention_summary or ""),
                "attention_count": attention_count,
                "loaded": _is_loaded(craft),
                "fleet_url": fleet_link(craft=craft.craft_id),
                "cargo_url": f"/cargo/manifests?mission={mission_filter}" if mission_filter else "/cargo/manifests",
                "cargo_audit_url": data_tab_link("cargo_audit", mission=mission_filter) if mission_filter else data_tab_link("cargo_audit"),
                "route_url": data_tab_link("routes", route=route) if route else data_tab_link("routes"),
                "fuel_url": data_tab_link("return_fuel", object=craft.craft_id),
                "body_url": data_tab_link("bodies", object=craft.current_object_id) if craft.current_object_id else data_tab_link("bodies"),
            }
        )
    return rows


def fleet_summary_metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(rows),
        "idle": sum(1 for row in rows if row["bucket"] == "Idle"),
        "active": sum(1 for row in rows if row["bucket"] == "Active"),
        "planned": sum(1 for row in rows if row["bucket"] == "Planned"),
        "loaded": sum(1 for row in rows if row["loaded"]),
        "people": sum(1 for row in rows if row["people_count"]),
        "attention": sum(1 for row in rows if row["attention_count"]),
    }


def idle_location_rows(rows: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["bucket"] == "Idle":
            grouped[str(row["location"])].append(row)
    result = []
    for location, craft_rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]:
        names = ", ".join(str(row["craft"]) for row in craft_rows[:4])
        if len(craft_rows) > 4:
            names = f"{names}, +{len(craft_rows) - 4} more"
        result.append(
            {
                "location": location,
                "count": len(craft_rows),
                "craft": names,
                "url": fleet_link(object=craft_rows[0]["location_id"], state="Idle")
                if craft_rows[0].get("location_id")
                else fleet_link(location=location, state="Idle"),
            }
        )
    return result


def filter_options(rows: list[dict[str, Any]], *, row_key: str, all_label: str) -> list[str]:
    return [all_label] + sorted({str(row[row_key]) for row in rows if row.get(row_key) not in (None, "", "-")})


def selected_filter_value(options: list[str], requested: str, fallback: str) -> str:
    return requested if requested in options else fallback


def fleet_row_matches_filters(row: dict[str, Any], filters: dict[str, str]) -> bool:
    craft_filter = filters.get("craft", "")
    if craft_filter and craft_filter not in {str(row["craft_id"]), str(row["craft"])}:
        return False
    mission_filter = filters.get("mission", "")
    if mission_filter and mission_filter != str(row.get("mission") or ""):
        return False
    route_filter = filters.get("route", "")
    if route_filter and route_filter != str(row.get("assignment") or ""):
        return False
    object_filter = filters.get("object", "")
    if object_filter and object_filter not in {str(row.get("location_id") or ""), str(row.get("location") or "")}:
        return False
    if filters.get("company", FILTER_ALL_COMPANIES) != FILTER_ALL_COMPANIES and row["company"] != filters["company"]:
        return False
    if filters.get("status", FILTER_ALL_STATUSES) != FILTER_ALL_STATUSES and row["status"] != filters["status"]:
        return False
    if filters.get("location", FILTER_ALL_LOCATIONS) != FILTER_ALL_LOCATIONS and row["location"] != filters["location"]:
        return False
    if filters.get("type", FILTER_ALL_TYPES) != FILTER_ALL_TYPES and row["type"] != filters["type"]:
        return False
    state_filter = filters.get("state", FILTER_ALL_STATES)
    if state_filter != FILTER_ALL_STATES and row["bucket"] != state_filter:
        return False
    cargo_filter = filters.get("cargo", FILTER_ALL_CARGO)
    if cargo_filter == FILTER_CARGO_PRESENT and not row["loaded"]:
        return False
    if cargo_filter == FILTER_CARGO_EMPTY and row["loaded"]:
        return False
    people_filter = filters.get("people", FILTER_ALL_PEOPLE)
    if people_filter == FILTER_PEOPLE_CONTEXT and not row["people_context"]:
        return False
    if people_filter == FILTER_PEOPLE_ABOARD and int(row["people_count"]) <= 0:
        return False
    if people_filter == FILTER_EMPTY_SEATS and int(row["empty_seats"]) <= 0:
        return False
    if people_filter == FILTER_NO_PEOPLE_CONTEXT and row["people_context"]:
        return False
    warning_filter = filters.get("warning", FILTER_ALL_WARNINGS)
    has_warning = bool(row["attention_count"] or str(row["warnings"] or "") not in ("", "-"))
    if warning_filter == FILTER_WARNINGS and not has_warning:
        return False
    if warning_filter == FILTER_CLEAN and has_warning:
        return False
    assignment_filter = filters.get("assignment", FILTER_ALL_ASSIGNMENTS)
    if assignment_filter == FILTER_ASSIGNED and row["assignment"] == "-":
        return False
    if assignment_filter == FILTER_UNASSIGNED and row["assignment"] != "-":
        return False
    if assignment_filter == FILTER_ACTIVE_ASSIGNMENT and row["bucket"] != "Active":
        return False
    if assignment_filter == FILTER_PLANNED_ASSIGNMENT and row["bucket"] != "Planned":
        return False
    return True


def sort_fleet_rows(rows: list[dict[str, Any]], sort_filter: str = SORT_DEFAULT) -> list[dict[str, Any]]:
    if sort_filter == SORT_WARNINGS:
        return sorted(rows, key=lambda row: (-int(row["attention_count"]), str(row["craft"])))
    if sort_filter == SORT_STATE:
        return sorted(rows, key=lambda row: (str(row["bucket"]), str(row["craft"])))
    if sort_filter == SORT_LOCATION:
        return sorted(rows, key=lambda row: (str(row["location"]), str(row["craft"])))
    if sort_filter == SORT_ASSIGNMENT:
        return sorted(rows, key=lambda row: (str(row["assignment"]), str(row["craft"])))
    if sort_filter == SORT_TYPE:
        return sorted(rows, key=lambda row: (str(row["type"]), str(row["craft"])))
    if sort_filter == SORT_CRAFT:
        return sorted(rows, key=lambda row: (str(row["craft"]), int(row["craft_id"])))
    return list(rows)


def filter_fleet_rows(
    rows: list[dict[str, Any]],
    *,
    company_filter: str = FILTER_ALL_COMPANIES,
    status_filter: str = FILTER_ALL_STATUSES,
    location_filter: str = FILTER_ALL_LOCATIONS,
    type_filter: str = FILTER_ALL_TYPES,
    state_filter: str = FILTER_ALL_STATES,
    cargo_filter: str = FILTER_ALL_CARGO,
    people_filter: str = FILTER_ALL_PEOPLE,
    warning_filter: str = FILTER_ALL_WARNINGS,
    assignment_filter: str = FILTER_ALL_ASSIGNMENTS,
    sort_filter: str = SORT_DEFAULT,
    craft_filter: str = "",
    mission_filter: str = "",
    route_filter: str = "",
    object_filter: str = "",
) -> list[dict[str, Any]]:
    filters = {
        "company": company_filter,
        "status": status_filter,
        "location": location_filter,
        "type": type_filter,
        "state": state_filter,
        "cargo": cargo_filter,
        "people": people_filter,
        "warning": warning_filter,
        "assignment": assignment_filter,
        "craft": craft_filter,
        "mission": mission_filter,
        "route": route_filter,
        "object": object_filter,
    }
    return sort_fleet_rows([row for row in rows if fleet_row_matches_filters(row, filters)], sort_filter)


def _fleet_filter_params(
    *,
    company: str,
    status: str,
    location: str,
    type_value: str,
    state: str,
    cargo: str,
    people: str,
    warning: str,
    assignment: str,
    sort: str,
) -> dict[str, str]:
    defaults = {
        "company": FILTER_ALL_COMPANIES,
        "status": FILTER_ALL_STATUSES,
        "location": FILTER_ALL_LOCATIONS,
        "type": FILTER_ALL_TYPES,
        "state": FILTER_ALL_STATES,
        "cargo": FILTER_ALL_CARGO,
        "people": FILTER_ALL_PEOPLE,
        "warning": FILTER_ALL_WARNINGS,
        "assignment": FILTER_ALL_ASSIGNMENTS,
        "sort": SORT_DEFAULT,
    }
    values = {
        "company": company,
        "status": status,
        "location": location,
        "type": type_value,
        "state": state,
        "cargo": cargo,
        "people": people,
        "warning": warning,
        "assignment": assignment,
        "sort": sort,
    }
    return {key: value for key, value in values.items() if value and value != defaults[key]}


def fleet_filter_url(params: dict[str, str]) -> str:
    return fleet_link(**params)


def _render_fleet_kpis(rows: list[dict[str, Any]]) -> None:
    metrics = fleet_summary_metrics(rows)
    cards = (
        ("Fleet", metrics["total"], "craft detected in focused company scope", data_tab_link("fleet")),
        ("Idle", metrics["idle"], "craft without active assignments", "/fleet"),
        ("Active", metrics["active"], "en route or cyclical assignments", data_tab_link("routes")),
        ("Planned", metrics["planned"], "scheduled departures not launched", data_tab_link("routes")),
        ("Loaded", metrics["loaded"], "craft carrying cargo, fuel, or crew context", "/cargo/manifests"),
        ("People", metrics["people"], "craft carrying people", "/population/movement"),
        ("Warnings", metrics["attention"], "craft with direct attention rows", data_tab_link("attention")),
    )
    with ui.element("div").classes("population-kpis population-kpis-compact"):
        for label, value, hint, url in cards:
            with ui.link(target=str(url)).classes("population-kpi population-kpi-link"):
                ui.label(label).classes("population-kpi-label")
                ui.label(fmt_num(value)).classes("population-kpi-value")
                ui.label(hint).classes("population-kpi-hint")


def _render_idle_locations(rows: list[dict[str, Any]]) -> None:
    with ui.element("div").classes("dashboard-card"):
        with ui.row().classes("dashboard-title-row"):
            ui.label("Idle Craft By Location").classes("dashboard-card-title")
            ui.link("Body audit", data_tab_link("bodies")).classes("table-drilldown-link")
        locations = idle_location_rows(rows)
        if not locations:
            ui.label("No idle craft in the focused company scope.").classes("empty-state-note")
            return
        with ui.element("div").classes("overview-queue-list"):
            for location in locations:
                with ui.link(target=str(location["url"])).classes("overview-queue-row"):
                    ui.label(fmt_num(location["count"])).classes("overview-severity overview-severity-monitor")
                    with ui.element("div").classes("overview-queue-copy"):
                        ui.label(str(location["location"])).classes("overview-queue-title")
                        ui.label(str(location["craft"])).classes("overview-queue-message")
                        ui.label("Source: Body Board + Craft facts").classes("overview-queue-source")


def _render_priority_craft(rows: list[dict[str, Any]]) -> None:
    priority = sorted(
        rows,
        key=lambda row: (
            0 if row["attention_count"] else 1,
            0 if row["bucket"] == "Idle" else 1,
            str(row["location"]),
            str(row["craft"]),
        ),
    )[:8]
    with ui.element("div").classes("dashboard-card"):
        with ui.row().classes("dashboard-title-row"):
            ui.label("Ship Inventory Brief").classes("dashboard-card-title")
            ui.link("Fleet audit", data_tab_link("fleet")).classes("table-drilldown-link")
        if not priority:
            ui.label("No craft detected for the focused company scope.").classes("empty-state-note")
            return
        with ui.element("div").classes("fleet-brief-list"):
            for row in priority:
                with ui.element("div").classes("fleet-brief-row"):
                    with ui.element("div").classes("fleet-brief-main"):
                        ui.label(f"{row['craft']}").classes("overview-queue-title")
                        ui.label(f"{row['bucket']} at {row['location']} · {row['type']}").classes("overview-queue-message")
                        ui.label(f"Cargo: {row['cargo']} · Fuel: {row['fuel']}").classes("overview-queue-source")
                    with ui.row().classes("fleet-link-row"):
                        ui.link("Ship", str(row["fleet_url"])).classes("table-drilldown-link")
                        ui.link("Cargo", str(row["cargo_url"])).classes("table-drilldown-link")
                        ui.link("Route", str(row["route_url"])).classes("table-drilldown-link")
                        ui.link("Fuel", str(row["fuel_url"])).classes("table-drilldown-link")


def _render_roster(rows: list[dict[str, Any]], *, title: str = "Fleet Roster") -> None:
    columns = [
        {"name": "craft", "label": "Craft", "field": "craft", "sortable": True, "align": "left"},
        {"name": "type", "label": "Hull / Type", "field": "type", "sortable": True, "align": "left"},
        {"name": "bucket", "label": "State", "field": "bucket", "sortable": True, "align": "left"},
        {"name": "location", "label": "Location", "field": "location", "sortable": True, "align": "left"},
        {"name": "assignment", "label": "Assignment", "field": "assignment", "sortable": True, "align": "left"},
        {"name": "cargo", "label": "Cargo", "field": "cargo", "sortable": False, "align": "left"},
        {"name": "people", "label": "Crew / People", "field": "people", "sortable": False, "align": "left"},
        {"name": "fuel", "label": "Fuel Context", "field": "fuel", "sortable": False, "align": "left"},
        {"name": "warnings", "label": "Warnings", "field": "warnings", "sortable": False, "align": "left"},
        {"name": "links", "label": "Links", "field": "links", "sortable": False, "align": "left"},
    ]
    table = ui.table(columns=columns, rows=rows, row_key="key", pagination=12).classes("w-full fleet-roster-table")
    table.props("flat bordered dense wrap-cells")
    table.add_slot(
        "body-cell-links",
        r"""
        <q-td :props="props">
          <div class="fleet-table-links">
            <a class="table-drilldown-link" :href="props.row.fleet_url">Ship</a>
            <a class="table-drilldown-link" :href="props.row.cargo_url">Cargo</a>
            <a class="table-drilldown-link" :href="props.row.route_url">Route</a>
            <a class="table-drilldown-link" :href="props.row.fuel_url">Fuel</a>
            <a class="table-drilldown-link" :href="props.row.body_url">Body</a>
          </div>
        </q-td>
        """,
    )


def render_fleet_dashboard(
    analysis: SaveAnalysis,
    container: ui.element,
    initial_filters: dict[str, str] | None = None,
) -> None:
    rows = fleet_control_rows(analysis)
    requested_filters = initial_filters or {}
    with container:
        with ui.element("div").classes("dashboard-panel"):
            ui.label("Fleet Control").classes("section-card-title")
            ui.label("Ship inventory, idle craft, assignments, cargo/crew/fuel context, and source-linked drill-downs.").classes(
                "section-card-copy"
            )
            with ui.element("div").classes("chart-control-panel chart-control-panel-compact"):
                with ui.row().classes("chart-control-row"):
                    company_options = filter_options(rows, row_key="company", all_label=FILTER_ALL_COMPANIES)
                    status_options = filter_options(rows, row_key="status", all_label=FILTER_ALL_STATUSES)
                    location_options = filter_options(rows, row_key="location", all_label=FILTER_ALL_LOCATIONS)
                    type_options = filter_options(rows, row_key="type", all_label=FILTER_ALL_TYPES)
                    state_options = [FILTER_ALL_STATES, "Idle", "Active", "Planned"]
                    cargo_options = [FILTER_ALL_CARGO, FILTER_CARGO_PRESENT, FILTER_CARGO_EMPTY]
                    people_options = [
                        FILTER_ALL_PEOPLE,
                        FILTER_PEOPLE_CONTEXT,
                        FILTER_PEOPLE_ABOARD,
                        FILTER_EMPTY_SEATS,
                        FILTER_NO_PEOPLE_CONTEXT,
                    ]
                    warning_options = [FILTER_ALL_WARNINGS, FILTER_WARNINGS, FILTER_CLEAN]
                    assignment_options = [
                        FILTER_ALL_ASSIGNMENTS,
                        FILTER_ASSIGNED,
                        FILTER_UNASSIGNED,
                        FILTER_ACTIVE_ASSIGNMENT,
                        FILTER_PLANNED_ASSIGNMENT,
                    ]
                    sort_options = [
                        SORT_DEFAULT,
                        SORT_WARNINGS,
                        SORT_STATE,
                        SORT_LOCATION,
                        SORT_ASSIGNMENT,
                        SORT_TYPE,
                        SORT_CRAFT,
                    ]
                    company_select = ui.select(
                        options=company_options,
                        value=selected_filter_value(company_options, requested_filters.get("company", ""), FILTER_ALL_COMPANIES),
                        label="Company",
                    ).classes("chart-control")
                    status_select = ui.select(
                        options=status_options,
                        value=selected_filter_value(status_options, requested_filters.get("status", ""), FILTER_ALL_STATUSES),
                        label="Ship status",
                    ).classes("chart-control")
                    location_select = ui.select(
                        options=location_options,
                        value=selected_filter_value(location_options, requested_filters.get("location", ""), FILTER_ALL_LOCATIONS),
                        label="Location",
                    ).classes("chart-control")
                    type_select = ui.select(
                        options=type_options,
                        value=selected_filter_value(type_options, requested_filters.get("type", ""), FILTER_ALL_TYPES),
                        label="Hull / type",
                    ).classes("chart-control")
                    state_select = ui.select(
                        options=state_options,
                        value=selected_filter_value(state_options, requested_filters.get("state", ""), FILTER_ALL_STATES),
                        label="Fleet state",
                    ).classes("chart-control")
                    cargo_select = ui.select(
                        options=cargo_options,
                        value=selected_filter_value(cargo_options, requested_filters.get("cargo", ""), FILTER_ALL_CARGO),
                        label="Cargo",
                    ).classes("chart-control")
                    people_select = ui.select(
                        options=people_options,
                        value=selected_filter_value(people_options, requested_filters.get("people", ""), FILTER_ALL_PEOPLE),
                        label="People",
                    ).classes("chart-control")
                    warning_select = ui.select(
                        options=warning_options,
                        value=selected_filter_value(warning_options, requested_filters.get("warning", ""), FILTER_ALL_WARNINGS),
                        label="Warnings",
                    ).classes("chart-control")
                    assignment_select = ui.select(
                        options=assignment_options,
                        value=selected_filter_value(
                            assignment_options,
                            requested_filters.get("assignment", ""),
                            FILTER_ALL_ASSIGNMENTS,
                        ),
                        label="Assignment",
                    ).classes("chart-control")
                    sort_select = ui.select(
                        options=sort_options,
                        value=selected_filter_value(sort_options, requested_filters.get("sort", ""), SORT_DEFAULT),
                        label="Initial sort",
                    ).classes("chart-control")
                    summary = ui.label("").classes("chart-control-summary")
                    open_filtered = ui.button("Open filtered URL").props("outline dense").classes("table-drilldown-link")
                    clear_filter = ui.link("Clear filters", "/fleet").classes("table-drilldown-link")

            kpi_container = ui.column().classes("w-full")
            brief_container = ui.column().classes("w-full")
            roster_container = ui.column().classes("w-full")

            def selected_params() -> dict[str, str]:
                params = _fleet_filter_params(
                    company=str(company_select.value or FILTER_ALL_COMPANIES),
                    status=str(status_select.value or FILTER_ALL_STATUSES),
                    location=str(location_select.value or FILTER_ALL_LOCATIONS),
                    type_value=str(type_select.value or FILTER_ALL_TYPES),
                    state=str(state_select.value or FILTER_ALL_STATES),
                    cargo=str(cargo_select.value or FILTER_ALL_CARGO),
                    people=str(people_select.value or FILTER_ALL_PEOPLE),
                    warning=str(warning_select.value or FILTER_ALL_WARNINGS),
                    assignment=str(assignment_select.value or FILTER_ALL_ASSIGNMENTS),
                    sort=str(sort_select.value or SORT_DEFAULT),
                )
                for key in ("craft", "mission", "route", "object"):
                    if requested_filters.get(key):
                        params[key] = str(requested_filters[key])
                return params

            def selected_rows() -> list[dict[str, Any]]:
                return filter_fleet_rows(
                    rows,
                    company_filter=str(company_select.value or FILTER_ALL_COMPANIES),
                    status_filter=str(status_select.value or FILTER_ALL_STATUSES),
                    location_filter=str(location_select.value or FILTER_ALL_LOCATIONS),
                    type_filter=str(type_select.value or FILTER_ALL_TYPES),
                    state_filter=str(state_select.value or FILTER_ALL_STATES),
                    cargo_filter=str(cargo_select.value or FILTER_ALL_CARGO),
                    people_filter=str(people_select.value or FILTER_ALL_PEOPLE),
                    warning_filter=str(warning_select.value or FILTER_ALL_WARNINGS),
                    assignment_filter=str(assignment_select.value or FILTER_ALL_ASSIGNMENTS),
                    sort_filter=str(sort_select.value or SORT_DEFAULT),
                    craft_filter=str(requested_filters.get("craft") or ""),
                    mission_filter=str(requested_filters.get("mission") or ""),
                    route_filter=str(requested_filters.get("route") or ""),
                    object_filter=str(requested_filters.get("object") or ""),
                )

            def update_filtered_fleet() -> None:
                filtered_rows = selected_rows()
                params = selected_params()
                summary.text = f"Showing {len(filtered_rows)} of {len(rows)} craft; saved view: {fleet_filter_url(params)}"
                clear_filter.visible = bool(params)
                kpi_container.clear()
                brief_container.clear()
                roster_container.clear()
                with kpi_container:
                    _render_fleet_kpis(filtered_rows)
                with brief_container:
                    with ui.element("div").classes("dashboard-grid"):
                        _render_priority_craft(filtered_rows)
                        _render_idle_locations(filtered_rows)
                with roster_container:
                    with ui.element("div").classes("dashboard-card dashboard-card-wide"):
                        with ui.row().classes("dashboard-title-row"):
                            ui.label("Fleet Roster").classes("dashboard-card-title")
                            ui.link("Open source rows", data_tab_link("fleet")).classes("table-drilldown-link")
                        _render_roster(filtered_rows)

            open_filtered.on_click(lambda: ui.navigate.to(fleet_filter_url(selected_params())))
            for select in (
                company_select,
                status_select,
                location_select,
                type_select,
                state_select,
                cargo_select,
                people_select,
                warning_select,
                assignment_select,
                sort_select,
            ):
                select.on_value_change(lambda _: update_filtered_fleet())
            update_filtered_fleet()
