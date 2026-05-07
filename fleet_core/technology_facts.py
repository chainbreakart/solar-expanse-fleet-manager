from __future__ import annotations

from datetime import datetime
from typing import Any

from .fact_model import TechModifierFact, TechUnlockFact
from .normalizer_utils import extract_datetime, friendly_key, game_key, id_value, list_content, ref_value


RESEARCH_CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("research_sc_", "Spacecraft"),
    ("research_sails", "Spacecraft"),
    ("research_lv", "Launch"),
    ("research_launch", "Launch"),
    ("research_lifesup", "Life Support"),
    ("research_agriculture", "Life Support"),
    ("research_biotech", "Life Support"),
    ("research_terraforming", "Terraforming"),
    ("research_mining", "Mining"),
    ("research_power", "Power"),
    ("research_nuke", "Power"),
    ("research_robotics", "Automation"),
    ("research_category_", "Category"),
)


def research_category(research_id: str) -> str:
    for prefix, category in RESEARCH_CATEGORY_PREFIXES:
        if research_id.startswith(prefix):
            return category
    return "Research"


def research_display_name(research_id: str) -> str:
    if research_id.startswith("research_sc_"):
        return research_id.removeprefix("research_sc_").replace("_", " ").strip().title()
    display = friendly_key(research_id)
    return display or research_id


def research_id_from_value(value: Any) -> str:
    if isinstance(value, str):
        key = game_key(value)
        return key if key.startswith("research_") else ""
    if isinstance(value, dict):
        direct = game_key(value.get("id") or value.get("ID") or value.get("researchID") or value.get("ResearchID"))
        if direct.startswith("research_"):
            return direct
        for nested_key in (
            "researchDefinitionSave",
            "ResearchDefinitionSave",
            "researchDefinition",
            "ResearchDefinition",
            "rd",
        ):
            nested = research_id_from_value(value.get(nested_key))
            if nested:
                return nested
    raw = ref_value(value)
    key = raw.rsplit("/", 1)[-1] if raw else ""
    return key if key.startswith("research_") else ""


def progress_from_value(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    for key in ("progress", "Progress", "progress01", "Progress01"):
        raw = value.get(key)
        if isinstance(raw, (int, float)):
            return float(raw)
    return None


def unlock_date_from_value(value: Any) -> datetime | None:
    if not isinstance(value, dict):
        return None
    for key in ("unlockDate", "completedDate", "completeDate", "dateCompleted", "CompletedDate"):
        parsed = extract_datetime(value.get(key))
        if parsed:
            return parsed
    return None


def source_items(value: Any) -> list[Any]:
    if value is None:
        return []
    rows = list_content(value)
    if rows:
        return rows
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        values = value.get("$values")
        if isinstance(values, list):
            return values
    return []


def build_unlock_fact(
    *,
    company: str,
    research_id: str,
    status: str,
    progress: float | None,
    unlock_date: datetime | None,
    source_field: str,
    source_path: str,
    confidence: str,
    raw: dict[str, Any] | str | None,
) -> TechUnlockFact:
    return TechUnlockFact(
        company=company,
        research_id=research_id,
        display_name=research_display_name(research_id),
        category=research_category(research_id),
        status=status,
        progress=progress,
        unlock_date=unlock_date,
        source_field=source_field,
        source_path=source_path,
        confidence=confidence,
        raw=raw,
    )


def modifier_from_unlock(fact: TechUnlockFact) -> TechModifierFact:
    value = fact.status.lower().replace(" ", "_")
    return TechModifierFact(
        company=fact.company,
        research_id=fact.research_id,
        display_name=fact.display_name,
        category=fact.category,
        status=fact.status,
        target_type="research",
        target_key=fact.research_id,
        modifier_type="unlock_status",
        raw_value=value if fact.progress is None else f"{value}:{fact.progress:g}",
        adjusted_value=fact.progress,
        additive_value=None,
        multiplier=None,
        source_field=fact.source_field,
        source_path=fact.source_path,
        confidence=fact.confidence,
        raw=fact.raw,
    )


def append_research_rows(
    unlock_facts: list[TechUnlockFact],
    *,
    company: str,
    rows: list[Any],
    status: str,
    source_field: str,
    base_path: str,
    default_progress: float | None = None,
    confidence: str = "high",
) -> None:
    for index, row in enumerate(rows):
        research_id = research_id_from_value(row)
        if not research_id:
            continue
        progress = progress_from_value(row)
        if progress is None:
            progress = default_progress
        unlock_facts.append(
            build_unlock_fact(
                company=company,
                research_id=research_id,
                status=status,
                progress=progress,
                unlock_date=unlock_date_from_value(row),
                source_field=source_field,
                source_path=f"{base_path}.{source_field}[{index}]",
                confidence=confidence,
                raw=row if isinstance(row, dict) else str(row),
            )
        )


def build_tech_facts(
    companies: list[dict[str, Any]],
    included_companies: set[str] | None = None,
) -> tuple[list[TechUnlockFact], list[TechModifierFact]]:
    unlock_facts: list[TechUnlockFact] = []

    for company_index, company_row in enumerate(companies):
        company = str(id_value(company_row.get("companyID"), ""))
        if not company or (included_companies is not None and company not in included_companies):
            continue
        research = company_row.get("researchDataToSave")
        if not isinstance(research, dict):
            continue
        base_path = f"companyDataSave[{company_index}].researchDataToSave"

        append_research_rows(
            unlock_facts,
            company=company,
            rows=source_items(research.get("completeResearch")),
            status="Completed",
            source_field="completeResearch",
            base_path=base_path,
            default_progress=1.0,
        )
        append_research_rows(
            unlock_facts,
            company=company,
            rows=source_items(research.get("startNotFinish")),
            status="In Progress",
            source_field="startNotFinish",
            base_path=base_path,
            confidence="medium",
        )
        slot1 = research.get("slot1")
        if slot1:
            append_research_rows(
                unlock_facts,
                company=company,
                rows=[slot1],
                status="Active",
                source_field="slot1",
                base_path=base_path,
                confidence="high",
            )
        append_research_rows(
            unlock_facts,
            company=company,
            rows=source_items(research.get("queueRD")),
            status="Queued",
            source_field="queueRD",
            base_path=base_path,
            confidence="medium",
        )

    deduped: dict[tuple[str, str, str, str], TechUnlockFact] = {}
    for fact in unlock_facts:
        key = (fact.company, fact.research_id, fact.status, fact.source_field)
        deduped[key] = fact

    sorted_unlocks = sorted(
        deduped.values(),
        key=lambda fact: (fact.company, fact.status != "Active", fact.status, fact.category, fact.display_name, fact.research_id),
    )
    modifier_facts = [modifier_from_unlock(fact) for fact in sorted_unlocks]
    return sorted_unlocks, modifier_facts
