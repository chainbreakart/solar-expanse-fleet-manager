from __future__ import annotations

import sys
from pathlib import Path

from nicegui import ui

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

from fleet_core.analysis import analyze_save
from fleet_core.app_paths import app_dir, ensure_user_dirs, resource_root, server_host, server_port
from fleet_core.ipc import ensure_ipc_paths
from fleet_core.odin_save_parser import SaveParseError
from fleet_core.save_finder import SaveSlot, discover_saves
from fleet_modules import MODULES
from fleet_modules.people_transit import MODULE as PEOPLE_TRANSIT
from fleet_modules.population_dashboard import (
    population_flights,
    population_places,
    render_population_movement_dashboard,
    render_population_places_dashboard,
)
from fleet_modules.shared import TableModule

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

saves: list[SaveSlot] = discover_saves()
selected_save: SaveSlot | None = saves[0] if saves else None
save_options = {slot.label: slot for slot in saves}


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
    }


def apply_theme() -> None:
    ui.colors(primary="#35d8ff", secondary="#8fa7b5", accent="#ff9d2e", positive="#43e6a0")
    ui.add_css(STYLESHEET_PATH.read_text(encoding="utf-8"))


def render_nav(active: str) -> None:
    with ui.row().classes("section-nav"):
        for key, label, path in (
            ("overview", "Overview", "/"),
            ("population", "Population", "/population"),
            ("data", "Data Tables", "/data"),
        ):
            classes = "section-link section-link-active" if key == active else "section-link"
            ui.link(label, path).classes(classes)


def render_population_subnav(active: str) -> None:
    with ui.row().classes("subsection-nav"):
        for key, label, path in (
            ("hub", "Population Hub", "/population"),
            ("movement", "People Movement", "/population/movement"),
            ("places", "Colonies / Stations", "/population/places"),
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


def render_save_controls() -> tuple[ui.select, ui.checkbox]:
    select = ui.select(
        options=list(save_options.keys()),
        value=selected_save.label if selected_save else None,
        label="Save",
    ).classes("w-[520px] max-w-full")
    include_ai_and_wg = ui.checkbox("Include AI/WG companies", value=False).classes("ai-toggle")
    with include_ai_and_wg:
        ui.tooltip("Curiosity/debug view. Default stays focused on the player corporation.")
    return select, include_ai_and_wg


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


def render_overview_content(container, meta: dict[str, str]) -> None:
    container.clear()
    with container:
        with ui.element("div").classes("overview-grid"):
            with ui.element("div").classes("section-card"):
                ui.label("Population Logistics").classes("section-card-title")
                ui.label(
                    f"{meta.get('people_in_transit') or '-'} people moving, "
                    f"{meta.get('empty_crew_items') or '-'} empty crew holds, "
                    f"{meta.get('population_readiness_alerts') or '0'} destination concerns."
                ).classes("section-card-copy")
                ui.link("Open population dashboard", "/population").classes("section-link mt-3 inline-flex")
            with ui.element("div").classes("section-card"):
                ui.label("Data Tables").classes("section-card-title")
                ui.label(
                    "Fleet, route, body, people transit, and return-fuel boards for detailed inspection."
                ).classes("section-card-copy")
                ui.link("Open data tables", "/data").classes("section-link mt-3 inline-flex")
            with ui.element("div").classes("section-card"):
                ui.label("Topline Only").classes("section-card-title")
                ui.label(
                    "The index is intentionally quiet: save picker, global KPIs, and section navigation."
                ).classes("section-card-copy")


def render_population_hub_content(container, analysis, meta: dict[str, str]) -> None:
    container.clear()
    moving_people = meta.get("people_in_transit") or "0"
    flights = population_flights(analysis)
    places = population_places(analysis)
    places_with_concerns = sum(1 for row in places if row["status"] != "Safe")
    with container:
        with ui.element("div").classes("overview-grid"):
            with ui.element("div").classes("section-card"):
                ui.label("People Movement").classes("section-card-title")
                ui.label(
                    f"{moving_people} people moving across {len(flights)} detected flight rows. "
                    "Use this for in-transit manifests, arrival timing, destination readiness, and movement drill-downs."
                ).classes("section-card-copy")
                ui.link("Open people movement", "/population/movement").classes("section-link mt-3 inline-flex")
            with ui.element("div").classes("section-card"):
                ui.label("Colonies / Stations").classes("section-card-title")
                ui.label(
                    f"{len(places)} places have population, housing, or inbound people; "
                    f"{places_with_concerns} currently show sustainment concerns."
                ).classes("section-card-copy")
                ui.link("Open places dashboard", "/population/places").classes("section-link mt-3 inline-flex")
            with ui.element("div").classes("section-card"):
                ui.label("Growth / Sustainment").classes("section-card-title")
                ui.label(
                    "This will become the colony-growth layer: housing runway, Supply runway, queued capacity, and demand that has no inbound people."
                ).classes("section-card-copy")


@ui.page("/")
def overview_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("overview")
        ui.label("Solar Expanse Fleet Manager").classes("text-2xl font-semibold")
        ui.label("Topline movement status and section launcher.").classes("text-sm text-slate-600")
        status_label = ui.label("").classes("text-sm text-slate-600")
        metrics = ui.row().classes("gap-2")
        select, include_ai_and_wg = render_save_controls()
        content = ui.column().classes("w-full")

        def clear_page() -> None:
            render_metric_cards(metrics, empty_meta())
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = meta_with_module_metrics(analysis)
            render_metric_cards(metrics, meta)
            render_overview_content(content, meta)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select.on_value_change(lambda event: load_save(save_options.get(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        with ui.row().classes("toolbar"):
            ui.button("Reload", icon="refresh", on_click=lambda: load_save(save_options.get(select.value)))
            ui.label("Read-only MVP. It never writes to your save files.").classes("text-sm text-slate-600")
        load_save(selected_save)


@ui.page("/population")
def population_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        render_population_subnav("hub")
        ui.label("Population").classes("text-2xl font-semibold")
        ui.label("Section hub for people movement and colonies/stations sustainment.").classes("text-sm text-slate-600")
        status_label = ui.label("").classes("text-sm text-slate-600")
        metrics = ui.row().classes("gap-2")
        select, include_ai_and_wg = render_save_controls()
        content = ui.column().classes("w-full")

        def clear_page() -> None:
            render_metric_cards(metrics, empty_meta())
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = meta_with_module_metrics(analysis)
            render_metric_cards(metrics, meta)
            render_population_hub_content(content, analysis, meta)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select.on_value_change(lambda event: load_save(save_options.get(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        with ui.row().classes("toolbar"):
            ui.button("Reload", icon="refresh", on_click=lambda: load_save(save_options.get(select.value)))
            ui.label("Read-only MVP. It never writes to your save files.").classes("text-sm text-slate-600")
        load_save(selected_save)


@ui.page("/population/movement")
def population_movement_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        render_population_subnav("movement")
        ui.label("People Movement").classes("text-2xl font-semibold")
        ui.label("Flights, manifests, destination readiness, and in-transit drill-downs.").classes("text-sm text-slate-600")
        status_label = ui.label("").classes("text-sm text-slate-600")
        metrics = ui.row().classes("gap-2")
        select, include_ai_and_wg = render_save_controls()
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            render_metric_cards(metrics, empty_meta())
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = meta_with_module_metrics(analysis)
            render_metric_cards(metrics, meta)
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_population_movement_dashboard(analysis, dashboard_panel)
                with ui.element("div").classes("dashboard-card dashboard-card-wide"):
                    ui.label("People Transit Drill-Down").classes("dashboard-card-title")
                    mount_table(PEOPLE_TRANSIT, PEOPLE_TRANSIT.build_rows(analysis))
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select.on_value_change(lambda event: load_save(save_options.get(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        with ui.row().classes("toolbar"):
            ui.button("Reload", icon="refresh", on_click=lambda: load_save(save_options.get(select.value)))
            ui.label("Read-only MVP. It never writes to your save files.").classes("text-sm text-slate-600")
        load_save(selected_save)


@ui.page("/population/places")
def population_places_page() -> None:
    apply_theme()
    with ui.column().classes("app-shell w-full"):
        render_nav("population")
        render_population_subnav("places")
        ui.label("Colonies / Stations").classes("text-2xl font-semibold")
        ui.label("People in place, habitat capacity, Supply flow, and sustainment runway.").classes("text-sm text-slate-600")
        status_label = ui.label("").classes("text-sm text-slate-600")
        metrics = ui.row().classes("gap-2")
        select, include_ai_and_wg = render_save_controls()
        content = ui.column().classes("w-full gap-3")

        def clear_page() -> None:
            render_metric_cards(metrics, empty_meta())
            content.clear()

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = meta_with_module_metrics(analysis)
            render_metric_cards(metrics, meta)
            content.clear()
            with content:
                dashboard_panel = ui.column().classes("dashboard-panel")
                render_population_places_dashboard(analysis, dashboard_panel)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select.on_value_change(lambda event: load_save(save_options.get(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        with ui.row().classes("toolbar"):
            ui.button("Reload", icon="refresh", on_click=lambda: load_save(save_options.get(select.value)))
            ui.label("Read-only MVP. It never writes to your save files.").classes("text-sm text-slate-600")
        load_save(selected_save)


@ui.page("/data")
def data_page() -> None:
    apply_theme()
    module_tables: dict[str, ui.table] = {}
    module_tabs: dict[str, ui.tab] = {}
    with ui.column().classes("app-shell w-full"):
        render_nav("data")
        ui.label("Data Tables").classes("text-2xl font-semibold")
        ui.label("Full drill-down boards for fleet, route, body, people, and fuel inspection.").classes("text-sm text-slate-600")
        status_label = ui.label("").classes("text-sm text-slate-600")
        metrics = ui.row().classes("gap-2")
        select, include_ai_and_wg = render_save_controls()

        with ui.tabs().classes("w-full") as tabs:
            for module in MODULES:
                module_tabs[module.key] = ui.tab(module.label)

        first_tab = module_tabs[MODULES[0].key] if MODULES else None
        with ui.tab_panels(tabs, value=first_tab).classes("w-full"):
            for module in MODULES:
                with ui.tab_panel(module_tabs[module.key]):
                    module_tables[module.key] = mount_table(module)

        def clear_page() -> None:
            for table in module_tables.values():
                table.rows = []
                table.update()
            render_metric_cards(metrics, empty_meta())

        def load_save(slot: SaveSlot | None) -> None:
            analysis = load_analysis(slot, bool(include_ai_and_wg.value), status_label)
            if analysis is None or slot is None:
                clear_page()
                return
            meta = dict(analysis.meta)
            for module in MODULES:
                rows = module.build_rows(analysis)
                meta.update(module.build_metrics(analysis, rows))
                table = module_tables[module.key]
                table.rows = rows
                table.update()
            render_metric_cards(metrics, meta)
            status_label.text = status_message(analysis, slot, bool(include_ai_and_wg.value))

        select.on_value_change(lambda event: load_save(save_options.get(event.value)))
        include_ai_and_wg.on_value_change(lambda _: load_save(save_options.get(select.value)))
        with ui.row().classes("toolbar"):
            ui.button("Reload", icon="refresh", on_click=lambda: load_save(save_options.get(select.value)))
            ui.label("Read-only MVP. It never writes to your save files.").classes("text-sm text-slate-600")
        load_save(selected_save)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Solar Expanse Fleet Manager", host=server_host(), port=server_port(), reload=False)
