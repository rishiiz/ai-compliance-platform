"""Compare two policy versions: rule diff and optional impact count (new violations if new policy applied)."""

import hashlib
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import Policy, Rule
from app.services.external_db import get_external_engine
from app.services.rule_engine import RuleExecutionError, execute_rule

logger = logging.getLogger(__name__)


def _rule_identity_key(rule_data: dict) -> str:
    """Deterministic key for rule identity (entity, field, operator, value)."""
    entity = (rule_data.get("entity") or "").strip()
    field = (rule_data.get("field") or "").strip()
    operator = (rule_data.get("operator") or "=").strip()
    value = rule_data.get("value")
    canonical = json.dumps(
        {"entity": entity, "field": field, "operator": operator, "value": value},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _rule_to_summary(rule: Rule) -> dict:
    """Serialize rule for compare response."""
    rd = rule.rule_data or {}
    return {
        "id": rule.id,
        "policy_id": rule.policy_id,
        "rule_data": rd,
        "severity": rule.severity,
        "policy_clause_text": (rd.get("policy_clause_text") or "") if isinstance(rd, dict) else "",
    }


def compare_policies(
    db: Session,
    old_policy_id: int,
    new_policy_id: int,
    compute_impact: bool = True,
) -> dict[str, Any]:
    """
    Compare two policies by rule set. Returns rule diff and optionally new_violations_count.

    Args:
        db: Database session.
        old_policy_id: Policy ID for "old" version.
        new_policy_id: Policy ID for "new" version.
        compute_impact: If True and external DB is connected, run rules in only_in_new
                        and sum violating rows (estimated new violations if new policy adopted).

    Returns:
        {
            "old_policy": { id, name, version },
            "new_policy": { id, name, version },
            "only_in_old": [ rule summaries ],
            "only_in_new": [ rule summaries ],
            "in_both": [ rule summaries ],
            "impact": { "new_violations_count": int | None, "message": str }
        }
    """
    old_policy = db.query(Policy).filter(Policy.id == old_policy_id).first()
    new_policy = db.query(Policy).filter(Policy.id == new_policy_id).first()
    if not old_policy:
        raise ValueError(f"Policy not found: id={old_policy_id}")
    if not new_policy:
        raise ValueError(f"Policy not found: id={new_policy_id}")

    old_rules = (
        db.query(Rule)
        .filter(Rule.policy_id == old_policy_id)
        .all()
    )
    new_rules = (
        db.query(Rule)
        .filter(Rule.policy_id == new_policy_id)
        .all()
    )

    old_keys = {}
    for r in old_rules:
        if isinstance(r.rule_data, dict):
            k = _rule_identity_key(r.rule_data)
            old_keys[k] = _rule_to_summary(r)

    new_keys = {}
    for r in new_rules:
        if isinstance(r.rule_data, dict):
            k = _rule_identity_key(r.rule_data)
            new_keys[k] = _rule_to_summary(r)

    only_in_old = [v for k, v in old_keys.items() if k not in new_keys]
    only_in_new = [v for k, v in new_keys.items() if k not in old_keys]
    in_both = [v for k, v in new_keys.items() if k in old_keys]

    impact_new_violations: int | None = None
    impact_message = "Impact requires a connected external database."
    if compute_impact and only_in_new:
        engine = get_external_engine()
        if engine is not None:
            total = 0
            errors = 0
            for summary in only_in_new:
                rd = summary.get("rule_data")
                if not isinstance(rd, dict):
                    continue
                try:
                    rows = execute_rule(rd)
                    total += len(rows)
                except (RuleExecutionError, ValueError):
                    errors += 1
            impact_new_violations = total
            impact_message = (
                f"Estimated new violations if you adopt the new policy: {total} (based on current DB snapshot)."
                + (f" ({errors} rule(s) could not be executed.)" if errors else "")
            )
        else:
            impact_message = "Connect an external database (POST /database/connect) and re-run compare to see impact."
    elif not only_in_new:
        impact_message = "No new rules in the new policy; no additional violations from rule changes."

    return {
        "old_policy": {
            "id": old_policy.id,
            "name": old_policy.name,
            "version": old_policy.version,
        },
        "new_policy": {
            "id": new_policy.id,
            "name": new_policy.name,
            "version": new_policy.version,
        },
        "only_in_old": only_in_old,
        "only_in_new": only_in_new,
        "in_both": in_both,
        "impact": {
            "new_violations_count": impact_new_violations,
            "message": impact_message,
        },
    }
