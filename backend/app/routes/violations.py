"""Violation API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AuditLog, Rule, Violation

router = APIRouter(prefix="/violations", tags=["violations"])

VALID_STATUSES = {"pending", "approved", "dismissed", "resolved"}


def _violation_to_item(v) -> dict:
    """Serialize a Violation with rule/policy for list response."""
    rule = v.rule
    policy = rule.policy if rule else None
    return {
        "id": v.id,
        "rule_id": v.rule_id,
        "policy_id": policy.id if policy else None,
        "policy_name": policy.name if policy else None,
        "record_id": v.record_id,
        "status": v.status,
        "severity": rule.severity if rule else None,
        "explanation": v.explanation,
        "suggested_remediation": v.suggested_remediation,
        "policy_clause_text": v.policy_clause_text,
        "evidence_snapshot": v.evidence_snapshot,
        "detected_at": v.detected_at.isoformat() if v.detected_at else None,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "reviewer_notes": v.reviewer_notes,
    }


@router.get("")
def list_violations(
    db: Session = Depends(get_db),
    severity: str | None = Query(None, description="Filter by rule severity"),
    status: str | None = Query(None, description="Filter by status"),
) -> list:
    """List violations with optional severity and status filters."""
    q = (
        db.query(Violation)
        .options(joinedload(Violation.rule).joinedload(Rule.policy))
        .order_by(Violation.detected_at.desc())
    )
    if severity:
        q = q.join(Violation.rule).filter(Rule.severity == severity)
    if status:
        q = q.filter(Violation.status == status)
    rows = q.all()
    return [_violation_to_item(v) for v in rows]


class ViolationStatusUpdate(BaseModel):
    """Request body for PATCH /violations/{id}."""

    status: str
    reviewer_notes: str | None = None


@router.get("/{violation_id}/audit")
def get_violation_audit(
    violation_id: int,
    db: Session = Depends(get_db),
) -> list:
    """Audit trail for a single violation (history of status changes, etc.)."""
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "violation",
            AuditLog.entity_id == violation_id,
        )
        .order_by(AuditLog.timestamp.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "action_type": r.action_type,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "performed_by": r.performed_by,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "meta": r.meta,
        }
        for r in rows
    ]


@router.patch("/{violation_id}")
def update_violation_status(
    violation_id: int,
    body: ViolationStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Update a violation's status (and optionally reviewer_notes).
    Creates an audit log entry when status is changed.
    """
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {sorted(VALID_STATUSES)}",
        )

    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found")

    old_status = violation.status
    violation.status = body.status
    if body.reviewer_notes is not None:
        violation.reviewer_notes = body.reviewer_notes

    if old_status != body.status:
        db.add(
            AuditLog(
                action_type="status_changed",
                entity_type="violation",
                entity_id=violation.id,
                performed_by="system",
                meta={
                    "old_status": old_status,
                    "new_status": body.status,
                },
            )
        )

    db.commit()
    db.refresh(violation)

    return {
        "id": violation.id,
        "rule_id": violation.rule_id,
        "record_id": violation.record_id,
        "status": violation.status,
        "reviewer_notes": violation.reviewer_notes,
        "created_at": violation.created_at.isoformat() if violation.created_at else None,
    }
