"""Rules list, create, and delete API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Policy, Rule
from app.schemas.rule_data import validate_rule_data

router = APIRouter(prefix="/rules", tags=["rules"])


class CreateRuleBody(BaseModel):
    """Body for creating a rule manually."""
    policy_id: int
    severity: str = "medium"
    policy_clause_text: str = ""


@router.get("")
def list_rules(
    db: Session = Depends(get_db),
    severity: str | None = Query(None, description="Filter by severity"),
) -> list:
    """List all rules with policy name."""
    q = (
        db.query(Rule)
        .options(joinedload(Rule.policy))
        .order_by(Rule.created_at.desc())
    )
    if severity:
        q = q.filter(Rule.severity == severity)
    rows = q.all()
    out = []
    for r in rows:
        policy = r.policy
        clause = (r.rule_data or {}).get("policy_clause_text") or ""
        out.append({
            "id": r.id,
            "policy_id": r.policy_id,
            "policy_name": policy.name if policy else None,
            "rule_data": r.rule_data,
            "severity": r.severity,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "policy_clause_text": clause,
        })
    return out


@router.post("")
def create_rule(
    body: CreateRuleBody,
    db: Session = Depends(get_db),
) -> dict:
    """Create a rule manually (linked to a policy)."""
    policy = db.query(Policy).filter(Policy.id == body.policy_id).first()
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
        policy_id=body.policy_id,
        rule_data=validated,
        severity=severity,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {
        "id": rule.id,
        "policy_id": rule.policy_id,
        "policy_name": policy.name,
        "rule_data": rule.rule_data,
        "severity": rule.severity,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "policy_clause_text": clause,
    }


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Delete a rule by id."""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"id": rule_id, "deleted": True}
