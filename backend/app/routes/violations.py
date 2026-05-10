"""Violation API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.audit_log import AuditLog
from app.models.rule import Rule
from app.models.violation import Violation

router = APIRouter(prefix="/violations", tags=["violations"])

VALID_STATUSES = {"pending", "approved", "dismissed", "resolved"}


def _violation_to_item(v) -> dict:
    """Serialize a Violation with rule/policy for list response."""
    rule = Rule.objects(id=v.rule_id).first() if v.rule_id else None
    policy = getattr(rule, 'policy_id', None) if rule else None
    return {
        "id": str(v.id),
        "rule_id": str(v.rule_id) if v.rule_id else None,
        "policy_id": str(policy.id) if hasattr(policy, 'id') else str(policy) if policy else None,
        "policy_name": policy.name if hasattr(policy, 'name') else None,
        "record_id": v.record_id,
        "status": v.status,
        "severity": rule.severity if rule else None,
        "explanation": v.explanation,
        "suggested_remediation": v.suggested_remediation,
        "policy_clause_text": v.policy_clause_text,
        "evidence_snapshot": v.evidence_snapshot,
        "detected_at": v.detected_at.isoformat() if v.detected_at else None,
        "created_at": v.created_at.isoformat() if hasattr(v, 'created_at') and v.created_at else None,
        "reviewer_notes": v.reviewer_notes,
    }


@router.get("")
def list_violations(
    severity: str | None = Query(None, description="Filter by rule severity"),
    status: str | None = Query(None, description="Filter by status"),
) -> list:
    """List violations with optional severity and status filters."""
    q = Violation.objects().order_by("-detected_at")
    
    # Filter by severity requires joining/filtering rules first
    if severity:
        matching_rules = Rule.objects(severity=severity).only('id')
        rule_ids = [str(r.id) for r in matching_rules]
        q = q.filter(rule_id__in=rule_ids)
        
    if status:
        q = q.filter(status=status)
    rows = q
    return [_violation_to_item(v) for v in rows]


class ViolationStatusUpdate(BaseModel):
    """Request body for PATCH /violations/{id}."""

    status: str
    reviewer_notes: str | None = None


@router.get("/{violation_id}/audit")
def get_violation_audit(
    violation_id: str,
) -> list:
    """Audit trail for a single violation (history of status changes, etc.)."""
    rows = AuditLog.objects(
        entity_type="violation",
        entity_id=violation_id,
    ).order_by("-timestamp")
    return [
        {
            "id": str(r.id),
            "action_type": r.action_type,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "performed_by": r.performed_by,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "meta": r.meta_data,
        }
        for r in rows
    ]


@router.patch("/{violation_id}")
def update_violation_status(
    violation_id: str,
    body: ViolationStatusUpdate,
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

    violation = Violation.objects(id=violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found")

    old_status = violation.status
    violation.status = body.status
    if body.reviewer_notes is not None:
        violation.reviewer_notes = body.reviewer_notes

    if old_status != body.status:
        AuditLog(
            action_type="status_changed",
            entity_type="violation",
            entity_id=str(violation.id),
            performed_by="system",
            meta_data={
                "old_status": old_status,
                "new_status": body.status,
            },
        ).save()

    violation.save()

    return {
        "id": str(violation.id),
        "rule_id": str(violation.rule_id),
        "record_id": violation.record_id,
        "status": violation.status,
        "reviewer_notes": violation.reviewer_notes,
        "created_at": violation.created_at.isoformat() if hasattr(violation, 'created_at') and violation.created_at else None,
    }
