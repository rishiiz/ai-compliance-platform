"""Compliance scan service: run scan, upsert violations, mark resolved."""

import logging
import time
from datetime import datetime, timezone

from app.models.rule import Rule
from app.models.violation import Violation
from app.services.explanation_service import (
    generate_remediation_suggestion,
    generate_violation_explanation,
)
from app.services.rule_engine import (
    RuleExecutionError,
    execute_rule,
    get_entity_count,
    get_rule_query,
)

logger = logging.getLogger(__name__)


def _record_id_from_row(row: dict) -> str:
    """Derive a stable record_id from a violating row."""
    for key in ("id", "id_", "pk", "ID"):
        if key in row and row[key] is not None:
            return str(row[key])
    if row:
        first_val = next(iter(row.values()), None)
        if first_val is not None:
            return str(first_val)
    return "unknown"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def run_scan(db=None) -> dict:
    """
    Run full compliance scan: execute all rules, upsert violations (new or update existing),
    mark violations as resolved when no longer present in current results.

    Returns:
        Dict with rules_checked, total_violations, resolved_count, by_rule.
    """
    rules = Rule.objects()
    if not rules:
        logger.info("Scan skipped: no rules to run")
        return {
            "rules_checked": 0,
            "total_violations": 0,
            "resolved_count": 0,
            "by_rule": [],
        }

    logger.info("Scan started | rules_count=%s", len(rules))
    total_violations = 0
    resolved_count = 0
    by_rule = []

    for rule in rules:
        rule_data = rule.rule_data
        if not isinstance(rule_data, dict):
            continue
        try:
            sql_query, _ = get_rule_query(rule_data)
            t0 = time.perf_counter()
            rows = execute_rule(rule_data)
            execution_time_ms = round((time.perf_counter() - t0) * 1000)
        except (RuleExecutionError, ValueError) as e:
            msg = str(e).lower()
            # Skip rules whose table/column doesn't exist in the company DB instead of failing the whole scan
            if "does not exist" in msg or "undefinedtable" in msg or "relation" in msg or "column" in msg:
                logger.warning(
                    "Skipping rule (table/column missing in company DB) | rule_id=%s | entity=%s | error=%s",
                    str(rule.id),
                    rule_data.get("entity"),
                    str(e),
                )
                continue
            logger.error(
                "Rule execution failed | rule_id=%s | entity=%s | error=%s",
                str(rule.id),
                rule_data.get("entity"),
                str(e),
                exc_info=True,
            )
            raise e

        rows_violated = len(rows)
        rows_scanned = get_entity_count(rule_data)
        logger.info(
            "Rule executed | rule_id=%s | entity=%s | execution_time_ms=%s | rows_scanned=%s | rows_violated=%s",
            str(rule.id),
            rule_data.get("entity"),
            execution_time_ms,
            rows_scanned,
            rows_violated,
        )

        policy_clause_text = (
            rule_data.get("policy_clause_text")
            if isinstance(rule_data.get("policy_clause_text"), str)
            else None
        )
        current_record_ids = set()
        count = 0
        policy_id_str = str(rule.policy_id.id) if hasattr(rule.policy_id, 'id') else str(rule.policy_id)

        for row in rows:
            record_id = _record_id_from_row(row)
            current_record_ids.add(record_id)
            try:
                explanation = generate_violation_explanation(
                    rule_data, row, sql_query, policy_id=policy_id_str
                )
            except Exception:
                explanation = (
                    "Violation detected based on rule condition. "
                    "AI explanation unavailable."
                )
            try:
                suggested_remediation = generate_remediation_suggestion(
                    rule_data, row, explanation, policy_id=policy_id_str
                )
            except Exception:
                suggested_remediation = None

            existing = Violation.objects(rule_id=rule.id, record_id=record_id).first()
            if existing:
                existing.evidence_snapshot = row
                existing.sql_query = sql_query
                existing.explanation = explanation
                existing.suggested_remediation = suggested_remediation
                existing.policy_clause_text = policy_clause_text
                existing.detected_at = _now_utc()
                if existing.status == "resolved":
                    existing.status = "pending"
                    existing.resolved_at = None
                existing.save()
                count += 1
            else:
                violation = Violation(
                    rule_id=rule.id,
                    record_id=record_id,
                    evidence_snapshot=row,
                    sql_query=sql_query,
                    explanation=explanation,
                    suggested_remediation=suggested_remediation,
                    policy_clause_text=policy_clause_text,
                    status="pending",
                    detected_at=_now_utc(),
                )
                violation.save()
                count += 1

        # Mark resolved: violations for this rule with record_id not in current results
        to_resolve = Violation.objects(
            rule_id=rule.id, 
            status__in=["pending", "approved", "dismissed"],
            record_id__nin=list(current_record_ids) if current_record_ids else []
        )
        now = _now_utc()
        for v in to_resolve:
            v.status = "resolved"
            v.resolved_at = now
            v.save()
            resolved_count += 1

        total_violations += count
        by_rule.append({
            "rule_id": str(rule.id),
            "violations": count,
            "execution_time_ms": execution_time_ms,
            "rows_scanned": rows_scanned,
            "rows_violated": rows_violated,
        })

    logger.info(
        "Scan completed | rules_checked=%s | total_violations=%s | resolved_count=%s",
        len(rules),
        total_violations,
        resolved_count,
    )
    return {
        "rules_checked": len(rules),
        "total_violations": total_violations,
        "resolved_count": resolved_count,
        "by_rule": by_rule,
    }
