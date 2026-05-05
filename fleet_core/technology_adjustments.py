from __future__ import annotations

from .fact_model import TechAdjustedValue, TechReferenceCatalog, TechReferenceModifier, TechUnlockFact

COMPLETED_TECH_STATUSES = {"Completed"}


def completed_research_by_company(tech_unlock_facts: list[TechUnlockFact] | None) -> dict[str, set[str]]:
    completed: dict[str, set[str]] = {}
    for fact in tech_unlock_facts or []:
        if fact.status not in COMPLETED_TECH_STATUSES:
            continue
        completed.setdefault(fact.company, set()).add(fact.research_id)
    return completed


def unlocked_reference_modifiers(
    catalog: TechReferenceCatalog | None,
    tech_unlock_facts: list[TechUnlockFact] | None,
    company: str,
) -> tuple[TechReferenceModifier, ...]:
    if catalog is None:
        return ()
    completed = completed_research_by_company(tech_unlock_facts).get(company, set())
    modifiers: list[TechReferenceModifier] = []
    for research_id in sorted(completed):
        modifiers.extend(catalog.modifiers_by_research_id.get(research_id, ()))
    return tuple(modifiers)


def target_modifier(
    modifiers: tuple[TechReferenceModifier, ...],
    *,
    modifier_type: str,
    target_type: str,
    target_key: str,
) -> TechReferenceModifier | None:
    for modifier in modifiers:
        if (
            modifier.modifier_type == modifier_type
            and modifier.target_type == target_type
            and modifier.target_key == target_key
        ):
            return modifier
    return None


def summed_percent_multiplier(
    modifiers: tuple[TechReferenceModifier, ...],
    *,
    modifier_type: str,
    target_type: str,
    target_key: str,
) -> TechAdjustedValue | None:
    matching = [
        modifier
        for modifier in modifiers
        if modifier.modifier_type == modifier_type
        and modifier.target_type == target_type
        and modifier.target_key == target_key
        and modifier.numeric_value is not None
    ]
    if not matching:
        return None
    percent = sum(float(modifier.numeric_value or 0.0) for modifier in matching)
    multiplier = max(0.0, 1.0 + percent / 100.0)
    return TechAdjustedValue(
        raw_value=percent,
        adjusted_value=percent,
        multiplier=multiplier,
        source="; ".join(dict.fromkeys(modifier.source for modifier in matching)),
        confidence="medium" if any(modifier.confidence == "medium" for modifier in matching) else "high",
        basis=", ".join(modifier.research_id for modifier in matching),
    )


def capacity_reference_adjustment(
    modifiers: tuple[TechReferenceModifier, ...],
    *,
    target_key: str,
    modifier_type: str,
    raw_value: float | None,
    source: str,
) -> TechAdjustedValue | None:
    modifier = target_modifier(
        modifiers,
        modifier_type=modifier_type,
        target_type="spacecraft",
        target_key=target_key,
    )
    if modifier is None:
        return None
    return TechAdjustedValue(
        raw_value=raw_value,
        adjusted_value=raw_value,
        multiplier=1.0,
        source=f"{source}; {modifier.source}",
        confidence=modifier.confidence,
        basis=f"{modifier.research_id}:{modifier.modifier_type}",
    )


def spacecraft_percent_capacity_adjustment(
    modifiers: tuple[TechReferenceModifier, ...],
    *,
    target_key: str,
    modifier_type: str,
    raw_value: float | None,
    source: str,
) -> tuple[float | None, TechAdjustedValue | None]:
    matching = [
        modifier
        for modifier in modifiers
        if modifier.modifier_type == modifier_type
        and modifier.target_type == "spacecraft"
        and modifier.target_key in {target_key, "All"}
        and modifier.numeric_value is not None
    ]
    if raw_value is None or not matching:
        return raw_value, None
    percent = sum(float(modifier.numeric_value or 0.0) for modifier in matching)
    multiplier = max(0.0, 1.0 + percent / 100.0)
    adjusted = raw_value * multiplier
    return adjusted, TechAdjustedValue(
        raw_value=raw_value,
        adjusted_value=adjusted,
        multiplier=multiplier,
        source=f"{source}; " + "; ".join(dict.fromkeys(modifier.source for modifier in matching)),
        confidence="medium" if any(modifier.confidence == "medium" for modifier in matching) else "high",
        basis=", ".join(f"{modifier.research_id}:{modifier.modifier_type}" for modifier in matching),
    )


def transport_capacity_adjustment(
    modifiers: tuple[TechReferenceModifier, ...],
    *,
    module_key: str,
    raw_capacity: int | None,
) -> tuple[int | None, TechAdjustedValue | None]:
    modifier = target_modifier(
        modifiers,
        modifier_type="population_capacity_per_unit",
        target_type="module",
        target_key=module_key,
    )
    if modifier is None:
        return raw_capacity, None
    adjusted = int(modifier.numeric_value) if modifier.numeric_value is not None else raw_capacity
    return adjusted, TechAdjustedValue(
        raw_value=float(raw_capacity) if raw_capacity is not None else None,
        adjusted_value=float(adjusted) if adjusted is not None else None,
        multiplier=(float(adjusted) / float(raw_capacity)) if raw_capacity and adjusted is not None else None,
        source=modifier.source,
        confidence=modifier.confidence,
        basis=f"{modifier.research_id}:{modifier.modifier_type}",
    )


def life_support_consumption_adjustment(
    modifiers: tuple[TechReferenceModifier, ...],
    *,
    raw_demand: float,
    apply_to_saved_outtake: bool,
) -> tuple[float, TechAdjustedValue | None]:
    if apply_to_saved_outtake:
        return raw_demand, None
    adjustment = summed_percent_multiplier(
        modifiers,
        modifier_type="life_support_consumption_percent",
        target_type="population",
        target_key="All",
    )
    if adjustment is None or adjustment.multiplier is None:
        return raw_demand, None
    adjusted = raw_demand * adjustment.multiplier
    return adjusted, TechAdjustedValue(
        raw_value=raw_demand,
        adjusted_value=adjusted,
        multiplier=adjustment.multiplier,
        source=adjustment.source,
        confidence=adjustment.confidence,
        basis=adjustment.basis,
    )
