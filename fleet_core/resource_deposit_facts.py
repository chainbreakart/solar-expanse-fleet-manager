from __future__ import annotations

from typing import Any

from .fact_model import KnownResourceDepositFact, ObjectFact
from .normalizer_utils import as_bool, as_float, as_int, friendly_key, game_key, id_value, list_content

RESOURCE_STATE_NAMES = {
    0: "Solid",
    1: "Liquid",
    2: "Gas",
    4: "Underground",
}


def object_label(object_id: int, names: dict[int, str]) -> str:
    name = names.get(object_id, "")
    return f"{name} ({object_id})" if name else f"Object {object_id}"


def row_resource_key(row: dict[str, Any], observed: dict[str, Any]) -> str:
    return (
        game_key(row.get("resourceType"))
        or game_key(row.get("ResourceType"))
        or game_key(observed.get("resourceTypeIDSave"))
        or game_key(observed.get("ResourceTypeIDSave"))
    )


def row_resource_state(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return RESOURCE_STATE_NAMES.get(value, str(value) if value not in (None, "") else "")


def numeric_value(value: Any) -> float | None:
    direct = as_float(value)
    if direct is not None:
        return direct
    if isinstance(value, dict):
        for key in ("value", "Value", "$value"):
            direct = as_float(value.get(key))
            if direct is not None:
                return direct
    return None


def known_state(progress: float, preliminary: bool) -> str:
    if progress >= 1.0:
        return "Fully explored"
    if preliminary:
        return "Preliminary"
    return "Partially explored"


def build_known_resource_deposit_facts(
    save: dict[str, Any],
    object_facts: dict[int, ObjectFact],
    object_names: dict[int, str],
    resources: dict[str, str],
    included_companies: set[str] | None = None,
) -> list[KnownResourceDepositFact]:
    facts: list[KnownResourceDepositFact] = []
    for object_index, row in enumerate(list_content(save.get("objectInfoDatas"))):
        if not isinstance(row, dict):
            continue
        company = str(id_value(row.get("companyId"), ""))
        if included_companies is not None and company not in included_companies:
            continue
        object_id = row.get("id") if isinstance(row.get("id"), int) else as_int(row.get("id"))
        if object_id is None:
            continue
        object_fact = object_facts.get(object_id)
        for deposit_index, deposit in enumerate(list_content(row.get("listExploredResourcesRows"))):
            if not isinstance(deposit, dict):
                continue
            observed = deposit.get("observedData") or deposit.get("ObservedData") or {}
            if not isinstance(observed, dict):
                observed = {}

            progress = numeric_value(deposit.get("value") if "value" in deposit else deposit.get("Value")) or 0.0
            preliminary = bool(
                as_bool(deposit.get("preliminaryExplored"))
                or as_bool(deposit.get("PreliminaryExplored"))
                or False
            )
            if progress <= 0 and not preliminary:
                continue

            resource_key = row_resource_key(deposit, observed)
            if not resource_key:
                continue
            remaining = numeric_value(observed.get("value") if "value" in observed else observed.get("Value"))
            mining_factor = numeric_value(
                observed.get("miningFactor") if "miningFactor" in observed else observed.get("MiningFactor")
            )
            selected = bool(
                as_bool(deposit.get("selectedToMine"))
                or as_bool(deposit.get("SelectedToMine"))
                or False
            )
            source_path = (
                f"objectInfoDatas[{object_index}].listExploredResourcesRows[{deposit_index}]"
            )
            facts.append(
                KnownResourceDepositFact(
                    deposit_key=f"{company}:{object_id}:{resource_key}:{deposit_index}",
                    company=company,
                    object_id=object_id,
                    object_label=object_label(object_id, object_names),
                    object_type=object_fact.object_type if object_fact else "Unknown",
                    resource_key=resource_key,
                    resource_name=resources.get(resource_key) or friendly_key(resource_key) or resource_key,
                    known_state=known_state(progress, preliminary),
                    exploration_progress=min(max(progress, 0.0), 1.0),
                    remaining=remaining,
                    mining_factor=mining_factor,
                    resource_state=row_resource_state(
                        observed.get("resourceState") if "resourceState" in observed else observed.get("ResourceState")
                    ),
                    selected_to_mine=selected,
                    source_path=source_path,
                    confidence="high",
                    raw=deposit,
                )
            )
    return sorted(
        facts,
        key=lambda fact: (fact.company, fact.object_label, fact.resource_name, -fact.exploration_progress),
    )
