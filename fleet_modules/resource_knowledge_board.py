from __future__ import annotations

from fleet_core.analysis import SaveAnalysis
from fleet_core.normalizer_utils import fmt_num

from .shared import AUDIT_COLUMNS, TableModule, TableRow, resource_cell_slot, with_resource_icon

COLUMNS = [
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "location", "label": "Location", "field": "location", "sortable": True, "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "sortable": True, "align": "left"},
    {"name": "resource", "label": "Resource", "field": "resource", "sortable": True, "align": "left"},
    {"name": "knowledge", "label": "Knowledge", "field": "knowledge", "sortable": True, "align": "left"},
    {"name": "progress", "label": "Explored", "field": "progress", "sortable": True, "align": "right"},
    {"name": "remaining", "label": "Remaining", "field": "remaining", "sortable": True, "align": "right"},
    {"name": "mining_factor", "label": "Mining Factor", "field": "mining_factor", "sortable": True, "align": "right"},
    {"name": "state", "label": "State", "field": "state", "sortable": True, "align": "left"},
    {"name": "selected", "label": "Selected", "field": "selected", "sortable": True, "align": "left"},
    {"name": "source_path", "label": "Source Path", "field": "source_path", "sortable": True, "align": "left"},
] + AUDIT_COLUMNS


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    rows: list[TableRow] = []
    for fact in analysis.known_resource_deposit_facts:
        rows.append(
            with_resource_icon(
                {
                "key": fact.deposit_key,
                "company": fact.company,
                "location": fact.object_label,
                "object_id": fact.object_id,
                "type": fact.object_type,
                "resource_key": fact.resource_key,
                "resource": fact.resource_name,
                "knowledge": fact.known_state,
                "progress_value": fact.exploration_progress,
                "progress": f"{fact.exploration_progress * 100:.0f}%",
                "remaining_value": fact.remaining,
                "remaining": f"{fmt_num(fact.remaining)}t" if fact.remaining is not None else "",
                "mining_factor_value": fact.mining_factor,
                "mining_factor": fmt_num(fact.mining_factor) if fact.mining_factor is not None else "",
                "state": fact.resource_state,
                "selected": "yes" if fact.selected_to_mine else "no",
                "source_path": fact.source_path,
                "audit_source": "KnownResourceDepositFact from company-local listExploredResourcesRows",
                "confidence": fact.confidence,
                "anomaly_destination": "Resource Knowledge / Attention" if not fact.resource_key else "Resource Knowledge",
                }
            )
        )
    return rows


def build_metrics(_analysis: SaveAnalysis, rows: list[TableRow]) -> dict[str, str]:
    resources = {str(row["resource"]) for row in rows}
    locations = {str(row["location"]) for row in rows}
    preliminary = sum(1 for row in rows if row["knowledge"] == "Preliminary")
    return {
        "known_deposits": str(len(rows)),
        "resources": str(len(resources)),
        "locations": str(len(locations)),
        "preliminary": str(preliminary),
    }


MODULE = TableModule(
    key="resource_knowledge",
    label="Resource Knowledge",
    columns=COLUMNS,
    build_rows=build_rows,
    build_metrics=build_metrics,
    pagination=20,
    slots={"body-cell-resource": resource_cell_slot()},
)
