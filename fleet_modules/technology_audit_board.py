from __future__ import annotations

from fleet_core.analysis import SaveAnalysis

from .shared import AUDIT_COLUMNS, TableModule, TableRow


columns = [
    {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "left"},
    {"name": "company", "label": "Company", "field": "company", "sortable": True, "align": "left"},
    {"name": "category", "label": "Category", "field": "category", "sortable": True, "align": "left"},
    {"name": "research_id", "label": "Research ID", "field": "research_id", "sortable": True, "align": "left"},
    {"name": "title", "label": "Title", "field": "title", "sortable": True, "align": "left"},
    {"name": "progress", "label": "Progress", "field": "progress", "sortable": True, "align": "right"},
    {"name": "reference", "label": "Reference", "field": "reference", "sortable": True, "align": "left"},
    {"name": "modifiers", "label": "Reference Modifiers", "field": "modifiers", "sortable": True, "align": "left"},
    {"name": "source_path", "label": "Save Source", "field": "source_path", "sortable": True, "align": "left"},
    *AUDIT_COLUMNS,
]


def modifier_summary(analysis: SaveAnalysis, research_id: str) -> str:
    modifiers = analysis.technology_reference.modifiers_by_research_id.get(research_id, ())
    if not modifiers:
        return ""
    return "; ".join(
        f"{modifier.modifier_type}->{modifier.target_type}:{modifier.target_key}"
        for modifier in modifiers[:5]
    ) + (f"; + {len(modifiers) - 5} more" if len(modifiers) > 5 else "")


def build_rows(analysis: SaveAnalysis) -> list[TableRow]:
    rows: list[TableRow] = []
    unknown_ids = {
        row.research_id
        for row in analysis.tech_unlock_facts
        if row.research_id not in analysis.technology_reference.by_research_id
    }
    for fact in analysis.tech_unlock_facts:
        reference = analysis.technology_reference.by_research_id.get(fact.research_id)
        rows.append(
            {
                "key": f"{fact.company}:{fact.status}:{fact.research_id}:{fact.source_field}",
                "status": fact.status,
                "company": fact.company,
                "category": reference.category if reference else fact.category,
                "research_id": fact.research_id,
                "title": reference.title if reference else fact.display_name,
                "progress": "" if fact.progress is None else fact.progress,
                "reference": "known" if reference else "missing",
                "modifiers": modifier_summary(analysis, fact.research_id),
                "source_path": fact.source_path,
                "audit_source": "TechUnlockFact + TechReferenceCatalog",
                "confidence": fact.confidence if reference else "low",
                "anomaly_destination": "Attention / Technology" if fact.research_id in unknown_ids else "Technology Dashboard",
            }
        )
    return sorted(rows, key=lambda row: (str(row["company"]), str(row["status"]), str(row["category"]), str(row["research_id"])))


MODULE = TableModule(
    key="technology_audit",
    label="Technology Audit",
    columns=columns,
    build_rows=build_rows,
)
