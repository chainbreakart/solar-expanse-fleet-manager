from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .app_paths import user_data_dir

COLONY_PLAN_SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_plan_id(prefix: str = "plan") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass(frozen=True)
class EvidenceLink:
    label: str
    url: str
    source_type: str = ""
    source_id: str = ""
    confidence: str = ""


@dataclass(frozen=True)
class PlanRequirement:
    requirement_id: str
    label: str
    status: str = "planned"
    category: str = ""
    target_value: str = ""
    current_value: str = ""
    notes: str = ""
    evidence_links: tuple[EvidenceLink, ...] = ()


@dataclass(frozen=True)
class PlanMilestone:
    milestone_id: str
    label: str
    status: str = "planned"
    target_date: str = ""
    notes: str = ""
    evidence_links: tuple[EvidenceLink, ...] = ()


@dataclass(frozen=True)
class ColonyTemplate:
    template_id: str
    name: str
    objective_label: str = ""
    description: str = ""
    requirement_lines: tuple[PlanRequirement, ...] = ()
    milestone_lines: tuple[PlanMilestone, ...] = ()
    schema_version: int = COLONY_PLAN_SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class ColonyPlan:
    plan_id: str
    title: str
    company: str
    target_object_id: str
    target_object_name: str
    target_object_type: str = ""
    objective_label: str = ""
    template_id: str = ""
    status: str = "planned"
    priority: str = "normal"
    save_fingerprint: str = ""
    notes: str = ""
    requirement_lines: tuple[PlanRequirement, ...] = ()
    milestone_lines: tuple[PlanMilestone, ...] = ()
    evidence_links: tuple[EvidenceLink, ...] = ()
    schema_version: int = COLONY_PLAN_SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class InvalidPlanRecord:
    path: Path
    record_type: str
    message: str


@dataclass(frozen=True)
class ColonyPlanLibrary:
    plans: tuple[ColonyPlan, ...]
    templates: tuple[ColonyTemplate, ...]
    diagnostics: tuple[InvalidPlanRecord, ...]


def _require_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing required string field: {field_name}")
    return value


def _optional_string(payload: dict[str, Any], field_name: str, default: str = "") -> str:
    value = payload.get(field_name, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"field must be a string: {field_name}")
    return value


def _schema_version(payload: dict[str, Any]) -> int:
    version = payload.get("schema_version", COLONY_PLAN_SCHEMA_VERSION)
    if version != COLONY_PLAN_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema version: {version}")
    return int(version)


def _list_payload(payload: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
    value = payload.get(field_name, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"field must be a list: {field_name}")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{field_name}[{index}] must be an object")
        rows.append(item)
    return rows


def evidence_link_from_dict(payload: dict[str, Any]) -> EvidenceLink:
    return EvidenceLink(
        label=_require_string(payload, "label"),
        url=_require_string(payload, "url"),
        source_type=_optional_string(payload, "source_type"),
        source_id=_optional_string(payload, "source_id"),
        confidence=_optional_string(payload, "confidence"),
    )


def requirement_from_dict(payload: dict[str, Any]) -> PlanRequirement:
    return PlanRequirement(
        requirement_id=_require_string(payload, "requirement_id"),
        label=_require_string(payload, "label"),
        status=_optional_string(payload, "status", "planned"),
        category=_optional_string(payload, "category"),
        target_value=_optional_string(payload, "target_value"),
        current_value=_optional_string(payload, "current_value"),
        notes=_optional_string(payload, "notes"),
        evidence_links=tuple(evidence_link_from_dict(row) for row in _list_payload(payload, "evidence_links")),
    )


def milestone_from_dict(payload: dict[str, Any]) -> PlanMilestone:
    return PlanMilestone(
        milestone_id=_require_string(payload, "milestone_id"),
        label=_require_string(payload, "label"),
        status=_optional_string(payload, "status", "planned"),
        target_date=_optional_string(payload, "target_date"),
        notes=_optional_string(payload, "notes"),
        evidence_links=tuple(evidence_link_from_dict(row) for row in _list_payload(payload, "evidence_links")),
    )


def template_from_dict(payload: dict[str, Any]) -> ColonyTemplate:
    return ColonyTemplate(
        template_id=_require_string(payload, "template_id"),
        name=_require_string(payload, "name"),
        objective_label=_optional_string(payload, "objective_label"),
        description=_optional_string(payload, "description"),
        requirement_lines=tuple(requirement_from_dict(row) for row in _list_payload(payload, "requirement_lines")),
        milestone_lines=tuple(milestone_from_dict(row) for row in _list_payload(payload, "milestone_lines")),
        schema_version=_schema_version(payload),
        created_at=_optional_string(payload, "created_at", utc_now_iso()),
        updated_at=_optional_string(payload, "updated_at", utc_now_iso()),
    )


def plan_from_dict(payload: dict[str, Any]) -> ColonyPlan:
    return ColonyPlan(
        plan_id=_require_string(payload, "plan_id"),
        title=_require_string(payload, "title"),
        company=_require_string(payload, "company"),
        target_object_id=_require_string(payload, "target_object_id"),
        target_object_name=_require_string(payload, "target_object_name"),
        target_object_type=_optional_string(payload, "target_object_type"),
        objective_label=_optional_string(payload, "objective_label"),
        template_id=_optional_string(payload, "template_id"),
        status=_optional_string(payload, "status", "planned"),
        priority=_optional_string(payload, "priority", "normal"),
        save_fingerprint=_optional_string(payload, "save_fingerprint"),
        notes=_optional_string(payload, "notes"),
        requirement_lines=tuple(requirement_from_dict(row) for row in _list_payload(payload, "requirement_lines")),
        milestone_lines=tuple(milestone_from_dict(row) for row in _list_payload(payload, "milestone_lines")),
        evidence_links=tuple(evidence_link_from_dict(row) for row in _list_payload(payload, "evidence_links")),
        schema_version=_schema_version(payload),
        created_at=_optional_string(payload, "created_at", utc_now_iso()),
        updated_at=_optional_string(payload, "updated_at", utc_now_iso()),
    )


def record_to_dict(record: ColonyPlan | ColonyTemplate | PlanRequirement | PlanMilestone | EvidenceLink) -> dict[str, Any]:
    return asdict(record)


class ColonyPlanRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else user_data_dir() / "colony_planner"
        self.plans_dir = self.root / "plans"
        self.templates_dir = self.root / "templates"

    def ensure_dirs(self) -> None:
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def load_library(self) -> ColonyPlanLibrary:
        plans, plan_diagnostics = self._load_records(self.plans_dir, "plan", plan_from_dict)
        templates, template_diagnostics = self._load_records(self.templates_dir, "template", template_from_dict)
        return ColonyPlanLibrary(
            plans=tuple(sorted(plans, key=lambda plan: (plan.updated_at, plan.title), reverse=True)),
            templates=tuple(sorted(templates, key=lambda template: template.name)),
            diagnostics=tuple(plan_diagnostics + template_diagnostics),
        )

    def save_plan(self, plan: ColonyPlan) -> ColonyPlan:
        self.ensure_dirs()
        now = utc_now_iso()
        stored = replace(plan, updated_at=now, created_at=plan.created_at or now)
        self._write_json(self._plan_path(stored.plan_id), record_to_dict(stored))
        return stored

    def save_template(self, template: ColonyTemplate) -> ColonyTemplate:
        self.ensure_dirs()
        now = utc_now_iso()
        stored = replace(template, updated_at=now, created_at=template.created_at or now)
        self._write_json(self._template_path(stored.template_id), record_to_dict(stored))
        return stored

    def get_plan(self, plan_id: str) -> ColonyPlan | None:
        path = self._plan_path(plan_id)
        if not path.exists():
            return None
        return plan_from_dict(self._read_payload(path))

    def get_template(self, template_id: str) -> ColonyTemplate | None:
        path = self._template_path(template_id)
        if not path.exists():
            return None
        return template_from_dict(self._read_payload(path))

    def delete_plan(self, plan_id: str) -> bool:
        return self._delete(self._plan_path(plan_id))

    def delete_template(self, template_id: str) -> bool:
        return self._delete(self._template_path(template_id))

    def _plan_path(self, plan_id: str) -> Path:
        return self.plans_dir / f"{plan_id}.json"

    def _template_path(self, template_id: str) -> Path:
        return self.templates_dir / f"{template_id}.json"

    def _load_records(self, directory: Path, record_type: str, parser: Any) -> tuple[list[Any], list[InvalidPlanRecord]]:
        if not directory.exists():
            return [], []
        records: list[Any] = []
        diagnostics: list[InvalidPlanRecord] = []
        for path in sorted(directory.glob("*.json")):
            try:
                records.append(parser(self._read_payload(path)))
            except Exception as exc:
                diagnostics.append(InvalidPlanRecord(path=path, record_type=record_type, message=str(exc)))
        return records, diagnostics

    def _read_payload(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("record root must be an object")
        return payload

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(path)

    def _delete(self, path: Path) -> bool:
        if not path.exists():
            return False
        path.unlink()
        return True
