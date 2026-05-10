"""Audit log / history API (read-only). Uses existing AuditLog model."""

from fastapi import APIRouter, Query

from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    entity_type: str | None = Query(None, description="Filter by entity_type"),
    entity_id: str | None = Query(None, description="Filter by entity_id"),
) -> list:
    """List recent audit log entries (history)."""
    q = AuditLog.objects().order_by("-timestamp")
    if entity_type:
        q = q.filter(entity_type=entity_type)
    if entity_id is not None:
        q = q.filter(entity_id=entity_id)
    rows = q.skip(offset).limit(limit)
    return [
        {
            "id": str(r.id),
            "action_type": r.action_type,
            "entity_type": r.entity_type,
            "entity_id": str(r.entity_id),
            "performed_by": r.performed_by,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "meta": r.meta_data,
        }
        for r in rows
    ]
