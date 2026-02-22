"""Audit log / history API (read-only). Uses existing AuditLog model."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_log(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    entity_type: str | None = Query(None, description="Filter by entity_type"),
    entity_id: int | None = Query(None, description="Filter by entity_id"),
) -> list:
    """List recent audit log entries (history)."""
    q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)
    rows = q.offset(offset).limit(limit).all()
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
