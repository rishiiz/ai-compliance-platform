"""Rules list, create, and delete API."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.policy import Policy
from app.models.rule import Rule
from app.schemas.rule_data import validate_rule_data

router = APIRouter(prefix="/rules", tags=["rules"])


class CreateRuleBody(BaseModel):
    """Body for creating a rule manually."""
    policy_id: str
    severity: str = "medium"
    policy_clause_text: str = ""


@router.get("")
def list_rules(
    severity: str | None = Query(None, description="Filter by severity"),
) -> list:
    """List all rules with policy name."""
    q = Rule.objects().order_by("-created_at")
    if severity:
        q = q.filter(severity=severity)
    rows = q
    out = []
    for r in rows:
        # Load policy manually since ReferenceField lazily loads or we can just access it
        policy = r.policy_id
        clause = (r.rule_data or {}).get("policy_clause_text") or ""
        out.append({
            "id": str(r.id),
            "policy_id": str(policy.id) if hasattr(policy, 'id') else str(policy),
            "policy_name": policy.name if hasattr(policy, 'name') else None,
            "rule_data": r.rule_data,
            "severity": r.severity,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "policy_clause_text": clause,
        })
    return out


@router.post("")
def create_rule(
    body: CreateRuleBody,
) -> dict:
    """Create a rule manually (linked to a policy)."""
    policy = Policy.objects(id=body.policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    clause = (body.policy_clause_text or "").strip() or "Manual compliance rule."
    rule_data = {
        "entity": "policy_docs",
        "field": "compliance_verified",
        "condition": {"type": "boolean"},
        "operator": "=",
        "value": True,
        "severity": (body.severity or "medium").strip().lower(),
        "policy_clause_text": clause,
    }
    try:
        validated = validate_rule_data(rule_data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    severity = validated.get("severity") or "medium"
    rule = Rule(
        policy_id=policy,
        rule_data=validated,
        severity=severity,
    )
    rule.save()
    return {
        "id": str(rule.id),
        "policy_id": str(policy.id),
        "policy_name": policy.name,
        "rule_data": rule.rule_data,
        "severity": rule.severity,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "policy_clause_text": clause,
    }


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: str,
) -> dict:
    """Delete a rule by id."""
    rule = Rule.objects(id=rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.delete()
    return {"id": rule_id, "deleted": True}
