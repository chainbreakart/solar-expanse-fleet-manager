from __future__ import annotations

import sys
from pathlib import Path

from nicegui import app as nicegui_app, context, ui

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from fleet_core.analysis import analyze_save
from fleet_core.app_paths import app_dir, ensure_user_dirs, resolve_server_port, resource_root, server_host
from fleet_core.ipc import ensure_ipc_paths
from fleet_core.odin_save_parser import SaveParseError
from fleet_core.save_finder import SaveSlot, discover_saves, save_options_by_label, select_save_after_refresh
from fleet_modules import MODULES
from fleet_modules.cargo_dashboard import (
    render_cargo_dashboard,
    render_cargo_manifests_dashboard,
    render_cargo_movement_dashboard,
    render_cargo_receipts_dashboard,
)
from fleet_modules.fleet_dashboard import render_fleet_dashboard
from fleet_modules.overview_dashboard import render_overview_dashboard
from fleet_modules.people_transit import MODULE as PEOPLE_TRANSIT
from fleet_modules.population_dashboard import (
    render_population_hub_dashboard,
    render_population_movement_dashboard,
    render_population_places_dashboard,
)
from fleet_modules.production_dashboard import (
    render_production_balance_dashboard,
    render_production_dashboard,
    render_production_opportunities_dashboard,
    render_production_sites_dashboard,
)
from fleet_modules.shared import TableModule
from fleet_modules.technology_dashboard import render_technology_dashboard

REPO_ROOT = resource_root()
APP_ROOT = app_dir()
STYLESHEET_PATHS = (
    APP_ROOT / "assets" / "command_console.css",
    REPO_ROOT / "assets" / "command_console.css",
    REPO_ROOT / "products" / "apps" / "fleet_manager" / "assets" / "command_console.css",
)
STYLESHEET_PATH = next((path for path in STYLESHEET_PATHS if path.exists()), STYLESHEET_PATHS[0])
APP_DATA_DIR = ensure_user_dirs()
IPC_PATHS = ensure_ipc_paths()
nicegui_app.add_static_files("/fleet-assets", APP_ROOT / "assets")

saves: list[SaveSlot] = discover_saves()
selected_save: SaveSlot | None = saves[0] if saves else None
save_options = save_options_by_label(saves)


METRIC_KEYS = (
    ("Game Date", "current_time"),
    ("Save Version", "save_version"),
    ("Companies", "companies"),
    ("Craft", "craft_count"),
    ("People Moving", "people_in_transit"),
    ("Empty Crew Holds", "empty_crew_items"),
    ("Empty Seats", "empty_crew_seats"),
    ("Return Fuel Gaps", "return_fuel_shortfalls"),
)


APP_CSS = """
body { background: #f6f7f4; color: #172026; }
.app-shell { max-width: 1500px; margin: 0 auto; padding: 18px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.section-nav { gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 4px; }
.section-link {
    padding: 6px 10px;
    border: 1px solid #d8ded8;
    border-radius: 6px;
    background: #ffffff;
    color: #315c72;
    font-size: 13px;
    font-weight: 650;
    text-decoration: none;
}
.section-link-active { background: #315c72; color: #ffffff; border-color: #315c72; }
.overview-grid {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
    margin-top: 8px;
}
.section-card {
    min-height: 122px;
    padding: 14px;
    border: 1px solid #d8ded8;
    border-radius: 8px;
    background: #ffffff;
}
.section-card-title { font-size: 17px; font-weight: 750; color: #172026; }
.section-card-copy { margin-top: 6px; color: #64706d; font-size: 13px; line-height: 1.35; }
.metric { min-width: 120px; padding: 8px 10px; border: 1px solid #d8ded8; background: #ffffff; border-radius: 6px; }
.metric-label { font-size: 11px; color: #64706d; text-transform: uppercase; }
.metric-value { font-size: 16px; font-weight: 650; color: #172026; }
.dashboard-title-row {
    align-items: flex-end;
    justify-content: space-between;
    margin-top: 2px;
    margin-bottom: 6px;
}
.dashboard-panel {
    width: 100%;
    padding: 14px;
    border: 1px solid #d8ded8;
    border-radius: 8px;
    background: #eef2ed;
}
.population-kpis {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 10px;
    margin-bottom: 12px;
}
.population-kpi {
    min-height: 86px;
    padding: 10px 12px;
    border: 1px solid #d8ded8;
    border-radius: 6px;
    background: #ffffff;
}
.population-kpi-label { font-size: 11px; color: #64706d; text-transform: uppercase; }
.population-kpi-value { margin-top: 3px; font-size: 23px; font-weight: 750; color: #172026; }
.population-kpi-hint { margin-top: 3px; font-size: 12px; color: #64706d; line-height: 1.25; }
.dashboard-grid {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 12px;
    align-items: stretch;
}
.dashboard-card {
    min-width: 0;
    padding: 10px;
    border: 1px solid #d8ded8;
    border-radius: 6px;
    background: #ffffff;
}
.dashboard-card-wide {
    margin-bottom: 12px;
}
.dashboard-card-title {
    margin-bottom: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #172026;
}
.q-table td { vertical-align: top; }
.q-table tbody td { font-size: 13px; }
.warning-chip {
    display: inline-flex;
    align-items: center;
    min-height: 22px;
    padding: 2px 7px;
    border: 1px solid #d9822b;
    border-radius: 6px;
    background: #fff7ed;
    color: #8a3b12;
    font-weight: 650;
    cursor: help;
}
.readiness-chip {
    display: inline-flex;
    align-items: center;
    min-height: 22px;
    padding: 2px 7px;
    border-radius: 6px;
    font-weight: 650;
    cursor: help;
}
.readiness-safe { border: 1px solid #2f855a; background: #f0fff4; color: #276749; }
.readiness-warning { border: 1px solid #d9822b; background: #fff7ed; color: #8a3b12; }
.readiness-urgent { border: 1px solid #c05621; background: #fffaf0; color: #7b341e; }
.readiness-critical { border: 1px solid #c53030; background: #fff5f5; color: #822727; }
.return-fuel-tooltip {
    max-width: 460px;
    background: #172026;
    color: #f8fafc;
    font-size: 12px;
    line-height: 1.35;
}
.return-fuel-tooltip-title {
    margin-bottom: 6px;
    font-weight: 700;
}
.return-fuel-tooltip-line + .return-fuel-tooltip-line {
    margin-top: 3px;
}
.people-detail {
    margin: 4px 0 8px 42px;
    max-width: 980px;
    border: 1px solid #d8ded8;
    border-radius: 6px;
    background: #ffffff;
    overflow: hidden;
}
.people-detail-row {
    display: grid;
    grid-template-columns: minmax(180px, 1.5fr) minmax(72px, .6fr) repeat(4, minmax(58px, .45fr)) minmax(90px, .7fr);
    gap: 8px;
    padding: 7px 10px;
    align-items: center;
    border-top: 1px solid #edf0ed;
}
.people-detail-row:first-child { border-top: 0; }
.people-detail-header {
    background: #f6f7f4;
    color: #64706d;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}
"""


def empty_meta() -> dict[str, str]:
    return {
        "current_time": "",
        "save_version": "",
        "companies": "",
        "craft_count": "",
        "people_in_transit": "",
        "empty_crew_items": "",
        "empty_crew_seats": "",
        "return_fuel_shortfalls": "",
        "attention_count": "",
        "fuel_attention_count": "",
        "capacity_attention_count": "",
        "population_attention_count": "",
        "cargo_attention_count": "",
        "technology_attention_count": "",
    }


def set_selected_save(label: str | None) -> SaveSlot | None:
    """Remember the manually selected save for page-to-page navigation."""
    global selected_save
    if label is None:
        return selected_save
    slot = save_options.get(str(label))
    if slot is not None:
        selected_save = slot
    return slot


def refresh_available_saves(preferred_label: str | None = None) -> SaveSlot | None:
    """Rescan the save directory and preserve the best available selection."""
    global saves, save_options, selected_save
    previous_selection = selected_save
    saves = discover_saves()
    save_options = save_options_by_label(saves)
    selected_save = select_save_after_refresh(saves, preferred_label, previous_selection)
    return selected_save


def refresh_save_select(select: ui.select, preferred_label: str | None = None) -> SaveSlot | None:
    slot = refresh_available_saves(preferred_label)
    select.options = list(save_options.keys())
    select.value = slot.label if slot else None
    select.update()
    return slot


def apply_theme() -> None:
    ui.colors(primary="#35d8ff", secondary="#8fa7b5", accent="#ff9d2e", positive="#43e6a0")
    ui.add_css(STYLESHEET_PATH.read_text(encoding="utf-8"))


def render_nav(active: str) -> None:
    with ui.row().classes("section-nav"):
        for key, label, path in (
            ("overview", "Overview", "/"),
            ("fleet", "Fleet", "/fleet"),
            ("population", "Population", "/population"),
            ("cargo", "Cargo", "/cargo"),
            ("production", "Production", "/production"),
            ("technology", "Technology", "/technology"),
            ("data", "Data Tables", "/data"),
        ):
            classes = "section-link section-link-active" if key == active else "section-link"
            ui.link(label, path).classes(classes)


def render_population_subnav(active: str) -> None:
    with ui.row().classes("subsection-nav"):
        for key, label, path in (
            ("hub", "Overview", "/population"),
            ("movement", "Movement", "/population/movement"),
            ("places", "Places", "/population/places"),
        ):
            classes = "subsection-link subsection-link-active" if key == active else "subsection-link"
            ui.link(label, path).classes(classes)
        ui.label("Prep Watchlist").classes("subsection-link subsection-link-disabled")


def render_cargo_subnav(active: str) -> None:
    with ui.row().classes("subsection-nav"):
        for key, label, path in (
            ("hub", "Overview", "/cargo"),
            ("movement", "Movement", "/cargo/movement"),
            ("receipts", "Receipts", "/cargo/receipts"),
            ("manifests", "Manifests", "/cargo/manifests"),
        ):
            classes = "subsection-link subsection-link-active" if key == active else "subsection-link"
            ui.link(label, path).classes(classes)


def render_production_subnav(active: str) -> None:
    with ui.row().classes("subsection-nav"):
        for key, label, path in (
            ("hub", "Overview", "/production"),
            ("balance", "Balance", "/production/balance"),
            ("opportunities", "Opportunities", "/production/opportunities"),
            ("sites", "Site Stock", "/production/sites"),
        ):
            classes = "subsection-link subsection-link-active" if key == active else "subsection-link"
            ui.link(label, path).classes(classes)


def render_metric_cards(container, meta: dict[str, str]) -> None:
    container.clear()
    with container:
        for label, key in METRIC_KEYS:
            metric_class = f"metric metric-{key.replace('_', '-')}"
            with ui.element("div").classes(metric_class):
                ui.label(label).classes("metric-label")
                ui.label(meta.get(key, "") or "-").classes("metric-value")


def render_save_controls() -> tuple[ui.select, ui.checkbox, ui.button, ui.label]:
    refresh_available_saves(selected_save.label if selected_save else None)
    with ui.element("div").classes("save-control-bar"):
        with ui.row().classes("save-control-row"):
            select = ui.select(
                options=list(save_options.keys()),
                value=selected_save.label if selected_save else None,
                label="Save",
            ).classes("save-select")
            include_ai_and_wg = ui.checkbox("Include AI/WG companies", value=False).classes("ai-toggle")
            with include_ai_and_wg:
                ui.tooltip("Curiosity/debug view. Default stays focused on the player corporation.")
            reload_button = ui.button("Reload", icon="refresh").classes("save-reload")
            ui.label("Read-only MVP. It never writes to your save files.").classes("save-control-note")
        status_label = ui.label("").classes("save-status")
    return select, include_ai_and_wg, reload_button, status_label


def load_analysis(slot: SaveSlot | None, include_ai_and_wg: bool, status_label):
    if slot is None:
        status_label.text = "No saves found in the default save directory."
        return None
    try:
        status_label.text = f"Loading {slot.json_path} ..."
        return analyze_save(slot, REPO_ROOT, include_ai_and_wg=include_ai_and_wg)
    except (OSError, SaveParseError, ValueError) as exc:
        status_label.text = f"Could not load save: {exc}"
        return None


def status_message(analysis, slot: SaveSlot, include_ai_and_wg: bool) -> str:
    confidence = "authoritative" if analysis.player_company_authoritative else "inferred"
    if include_ai_and_wg:
        shown = ", ".join(sorted(analysis.active_companies)) or "none"
        if analysis.player_company:
            return (
                f"Loaded {slot.name}; player {analysis.player_company} "
                f"({confidence}: {analysis.player_company_source}); showing player plus AI/WG companies: {shown}"
            )
        return f"Loaded {slot.name}; player corporation not certain, showing expanded company scope: {shown}"
    if analysis.player_company:
        return (
            f"Loaded {slot.name}; showing player corporation: {analysis.player_company} "
            f"({confidence}: {analysis.player_company_source})"
        )
    shown = ", ".join(sorted(analysis.active_companies)) or "none"
    return f"Loaded {slot.name}; player corporation not certain, hiding AI/WG and showing: {shown}"


def meta_with_module_metrics(analysis) -> dict[str, str]:
    meta = dict(analysis.meta)
    for module in MODULES:
        rows = module.build_rows(analysis)
        meta.update(module.build_metrics(analysis, rows))
    return meta


def mount_table(module: TableModule, rows: list[dict[str, object]] | None = None):
    table = ui.table(
        columns=module.columns,
        rows=rows or [],
        row_key=module.row_key,
        pagination=module.pagination,
    ).classes("w-full")
    table.props("flat bordered dense wrap-cells")
    if module.slots:
        for slot_name, slot_template in module.slots.items():
            table.add_slot(slot_name, slot_template)
    return table


def movement_drilldown_filters() -> dict[str, str]:
    request = context.client.request
    params = request.query_params if request else {}
    return {
        key: str(params.get(key) or "")
        for key in ("mission", "destination", "state", "readiness")
        if params.get(key)
    }


def cargo_drilldown_filters() -> dict[str, str]:
    request = context.client.request
    params = request.query_params if request else {}
    return {
        key: str(params.get(key) or "")
        for key in ("support", "company", "status", "kind", "source", "destination", "item", "arrival", "mission")
        if params.get(key)
    }


def fleet_drilldown_filters() -> dict[str, str]:
    request = context.client.request
    params = request.query_params if request else {}
    return {
        key: str(params.get(key) or "")
        for key in (
            "company",
            "status",
            "location",
            "type",
            "state",
            "cargo",
            "people",
            "warning",
            "assignment",
            "sort",
            "craft",
            "mission",
            "route",
            "object",
        )
        if params.get(key)
    }


def requested_data_tab() -> str:
    request = context.client.request
    params = request.query_params if request else {}
    return str(params.get("tab") or "")


def requested_data_filters() -> dict[str, str]:
    request = context.client.request
    params = request.query_params if request else {}
    return {
        key: str(params.get(key) or "")
        for key in (
            "key",
            "company",
            "resource",
            "object",
            "mission",
            "status",
            "source",
            "destination",
            "route",
            "research_id",
            "category",
            "support",
        )
        if params.get(key)
    }


def row_filter_values(row: dict[str, object], *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        text = str(value)
        values.add(text)
        for separator in (";", ","):
            if separator in text:
                values.update(part.strip() for part in text.split(separator) if part.strip())
    return values


def data_row_matches_filters(row: dict[str, object], filters: dict[str, str]) -> bool:
    if not filters:
        return True
    row_key = filters.get("key")
    if row_key and row_key != str(row.get("key") or ""):
        return False
    company = filters.get("company")
    if company and str(row.get("company") or "") != company:
        return False
    resource = filters.get("resource")
    if resource:
        resource_values = row_filter_values(row, "resource_key", "resource", "resource_keys", "items", "top_cargo")
        if resource not in resource_values:
            return False
    object_id = filters.get("object")
    if object_id:
        object_values = row_filter_values(row, "object_id", "craft_id", "id", "source_id", "target_id", "location_id")
        object_labels = " ".join(str(row.get(key) or "") for key in ("location", "place", "body", "source", "destination", "route"))
        if object_id not in object_values and f"({object_id})" not in object_labels:
            return False
    mission = filters.get("mission")
    if mission and mission not in row_filter_values(row, "mission", "mission_id", "mission_key", "missions"):
        return False
    for key in ("status", "source", "destination", "route", "research_id", "category"):
        expected = filters.get(key)
        if expected and expected != str(row.get(key) or ""):
            return False
    support = filters.get("support")
    if support and support not in row_filter_values(row, "support", "support_classes"):
        return False
    return True


def filter_data_rows(rows: list[dict[str, object]], filters: dict[str, str]) -> list[dict[str, object]]:
    return [row for row in rows if data_row_matches_filters(row, filters)]


def people_row_matches_filter(row: dict[str, object], filters: dict[str, str]) -> bool:
    if not filters:
        return True
    mission = filters.get("mission")
    if mission and str(row.get("key") or "") != mission:
        return False
    destination = filters.get("destination")
    if destination and destination not in str(row.get("route") or ""):
        return False
    state = filters.get("state")
    if state == "loaded" and int(row.get("people") or 0) <= 0:
        return False
    if state == "empty" and not any(
        isinstance(detail, dict) and detail.get("state") == "Empty"
        for detail in row.get("details", [])
    ):
        return False
    if state == "empty_seats" and int(row.get("empty_seats") or 0) <= 0:
        return False
    if filters.get("readiness") == "attention" and row.get("readiness") not in {"Warning", "Urgent", "Critical"}:
        return False
    return True


def filter_people_rows(rows: list[dict[str, object]], filters: dict[str, str]) -> list[dict[str, object]]:
    return [row for row in rows if people_row_matches_filter(row, filters)]


def render_people_filter_banner(filters: dict[str, str], rows: list[dict[str, object]], total_rows: int) -> None:
    if not filters:
        return
    parts = []
    if filters.get("mission"):
        parts.append(f"mission {filters['mission'].split(':')[-1]}")
    if filters.get("destination"):
        parts.append(f"destination {filters['destination']}")
    if filters.get("state"):
        parts.append(filters["state"].replace("_", " "))
    if filters.get("readiness"):
        parts.append("readiness concerns")
    label = ", ".join(parts) or "filtered"
    with ui.element("div").classes("drilldown-filter-banner"):
        ui.label(f"People Transit filtered by {label}: {len(rows)} of {total_rows} rows").classes("drilldown-filter-text")
        ui.link("Clear filter", "/population/movement").classes("table-drilldown-link")


def render_overview_content(container, analysis, meta: dict[str, str]) -> None:
    container.clear()
    with container:
        render_overview_dashboard(analysis, meta)


def render_population_hub_content(container, analysis, meta: dict[str, str]) -> None:
    render_population_hub_dashboard(analysis, meta, container)


@ui.page("/fleet")
def fleet_page() -> None:
    apply_theme()
    drilldown_filters = fleet_drilldown_filters()
    with ui.column().classes("app-shell w-full"):
        render_nav("fleet")
        ui.label("Fleet Control").classes("text-2xl font-semibold")
        ui.label("Ship inventory, idle craft, assignments, cargo, crew, fuel context, and drill-downs.").classes(
            "text-sm text-slate-600"
        )
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            render_fleet_dashboard(analysis, content, drilldown_filters)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/")
def overview_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("overview")
        ui.label("Command Overview").classes("text-2xl font-semibold")
        ui.label("Colonies, supply lines, industry, and research at a glance.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = meta_with_module_metrics(analysis)
            render_overview_content(content, analysis, meta)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/population")
def population_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        render_population_subnav("hub")
        ui.label("Population").classes("text-2xl font-semibold")
        ui.label("Settlement pressure, migration flow, and sustainment at a glance.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = meta_with_module_metrics(analysis)
            render_population_hub_content(content, analysis, meta)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/population/movement")
def population_movement_page() -> None:
    apply_theme()
    drilldown_filters = movement_drilldown_filters()
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        render_population_subnav("movement")
        ui.label("People Movement").classes("text-2xl font-semibold")
        ui.label("Flights, manifests, destination readiness, and in-transit drill-downs.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_population_movement_dashboard(analysis, dashboard_panel)
                with ui.element("div").classes("dashboard-card dashboard-card-wide"):
                    ui.label("People Transit Drill-Down").classes("dashboard-card-title")
                    people_rows = PEOPLE_TRANSIT.build_rows(analysis)
                    filtered_rows = filter_people_rows(people_rows, drilldown_filters)
                    render_people_filter_banner(drilldown_filters, filtered_rows, len(people_rows))
                    mount_table(PEOPLE_TRANSIT, filtered_rows)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/population/places")
def population_places_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        render_population_subnav("places")
        ui.label("Place Sustainment").classes("text-2xl font-semibold")
        ui.label("People in place, habitat capacity, Supply flow, and sustainment runway.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_population_places_dashboard(analysis, dashboard_panel)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/cargo")
def cargo_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("cargo")
        render_cargo_subnav("hub")
        ui.label("Cargo").classes("text-2xl font-semibold")
        ui.label("Supply lanes, settlement cargo, receipts, and manifest evidence at a glance.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            render_cargo_dashboard(analysis, content)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/cargo/movement")
def cargo_movement_page() -> None:
    apply_theme()
    drilldown_filters = cargo_drilldown_filters()
    with ui.column().classes("app-shell w-full"):
        render_nav("cargo")
        render_cargo_subnav("movement")
        ui.label("Cargo Movement").classes("text-2xl font-semibold")
        ui.label("Route timing, in-transit matrix, and arrival schedule.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_cargo_movement_dashboard(analysis, dashboard_panel, drilldown_filters)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/cargo/receipts")
def cargo_receipts_page() -> None:
    apply_theme()
    drilldown_filters = cargo_drilldown_filters()
    with ui.column().classes("app-shell w-full"):
        render_nav("cargo")
        render_cargo_subnav("receipts")
        ui.label("Cargo Receipts").classes("text-2xl font-semibold")
        ui.label("Destination receipts joined to local production evidence.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_cargo_receipts_dashboard(analysis, dashboard_panel, drilldown_filters)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/cargo/manifests")
def cargo_manifests_page() -> None:
    apply_theme()
    drilldown_filters = cargo_drilldown_filters()
    with ui.column().classes("app-shell w-full"):
        render_nav("cargo")
        render_cargo_subnav("manifests")
        ui.label("Cargo Manifests").classes("text-2xl font-semibold")
        ui.label("Grouped manifest drill-downs for raw item and support inspection.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_cargo_manifests_dashboard(analysis, dashboard_panel, drilldown_filters)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/production")
def production_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("production")
        render_production_subnav("hub")
        ui.label("Production").classes("text-2xl font-semibold")
        ui.label("Industrial stockpiles, exporters, runway, and colony-prep evidence.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            render_production_dashboard(analysis, content)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/production/balance")
def production_balance_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("production")
        render_production_subnav("balance")
        ui.label("Production Balance").classes("text-2xl font-semibold")
        ui.label("Surpluses, deficits, exporter candidates, and sustainment runway.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_production_balance_dashboard(analysis, dashboard_panel)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/production/opportunities")
def production_opportunities_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("production")
        render_production_subnav("opportunities")
        ui.label("Resource Opportunities").classes("text-2xl font-semibold")
        ui.label("Known shortage-to-site candidates from visible stock, flow, route, and body evidence.").classes(
            "text-sm text-slate-600"
        )
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_production_opportunities_dashboard(analysis, dashboard_panel)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/production/sites")
def production_sites_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("production")
        render_production_subnav("sites")
        ui.label("Production Site Stock").classes("text-2xl font-semibold")
        ui.label("Candidate colony-support stock grouped by location.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_production_sites_dashboard(analysis, dashboard_panel)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/colony-planner")
def colony_planner_page() -> None:
    apply_theme()
    request = context.client.request
    params = request.query_params if request else {}
    resource = str(params.get("resource") or "")
    target = str(params.get("target") or "")
    objective = str(params.get("objective") or "")
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        ui.label("Colony Planner").classes("text-2xl font-semibold")
        ui.label("Saved plans and templates are not implemented yet; this page currently receives planning handoffs.").classes(
            "text-sm text-slate-600"
        )
        with ui.element("div").classes("dashboard-panel"):
            with ui.element("div").classes("dashboard-card dashboard-card-wide"):
                ui.label("Planning Handoff").classes("dashboard-card-title")
                if resource or target or objective:
                    ui.label(f"Objective: {objective or 'not specified'}").classes("section-card-copy")
                    ui.label(f"Resource: {resource or 'not specified'}").classes("section-card-copy")
                    ui.label(f"Target object: {target or 'not specified'}").classes("section-card-copy")
                    ui.link("Back to opportunities", "/production/opportunities").classes("table-drilldown-link")
                else:
                    ui.label("Open a Resource Opportunity row from Production to prefill this handoff.").classes(
                        "empty-state-note"
                    )


@ui.page("/technology")
def technology_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("technology")
        ui.label("Technology").classes("text-2xl font-semibold")
        ui.label("Focused-save research unlocks, active work, and tech effects used by planner math.").classes("text-sm text-slate-600")
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_technology_dashboard(analysis, dashboard_panel)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


@ui.page("/data")
def data_page() -> None:
    apply_theme()
    module_tables: dict[str, ui.table] = {}
    module_tabs: dict[str, ui.tab] = {}
    with ui.column().classes("app-shell w-full"):
        render_nav("data")
        ui.label("Data Tables").classes("text-2xl font-semibold")
        ui.label(
            "Flight-recorder boards for source rows, confidence, anomaly destinations, and detailed inspection."
        ).classes("text-sm text-slate-600")

        with ui.tabs().classes("w-full") as tabs:
            for module in MODULES:
                module_tabs[module.key] = ui.tab(module.label)

        requested_tab = requested_data_tab()
        requested_filters = requested_data_filters()
        default_key = MODULES[0].key if MODULES else ""
        first_tab = module_tabs.get(requested_tab) or module_tabs.get(default_key)
        with ui.tab_panels(tabs, value=first_tab).classes("w-full"):
            for module in MODULES:
                with ui.tab_panel(module_tabs[module.key]):
                    module_tables[module.key] = mount_table(module)

        def clear_page() -> None:
            for table in module_tables.values():
                table.rows = []
                table.update()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            for module in MODULES:
                rows = filter_data_rows(module.build_rows(analysis), requested_filters)
                table = module_tables[module.key]
                table.rows = rows
                table.update()
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select, include_ai_and_wg, reload_button, status_label = render_save_controls()
        select.on_value_change(lambda event: load_save(set_selected_save(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        reload_button.on_click(lambda: load_save(refresh_save_select(select, select.value)))
        load_save(selected_save)


def run_server() -> None:
    host = server_host()
    try:
        port, startup_notes = resolve_server_port(host)
    except RuntimeError as exc:
        print(f"Solar Expanse Fleet Manager could not start: {exc}", file=sys.stderr, flush=True)
        sys.exit(2)
    for note in startup_notes:
        print(note, flush=True)
    print(f"Open Solar Expanse Fleet Manager at http://{host}:{port}", flush=True)
    ui.run(title="Solar Expanse Fleet Manager", host=host, port=port, reload=False, show=False)


if __name__ in {"__main__", "__mp_main__"}:
    run_server()
