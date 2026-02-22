"""Profile and activity (history) API. All metrics and activity are per-user (current authenticated user)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.routes.auth_routes import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class TrackActionBody(BaseModel):
    action_type: str = "report_viewed"


def _start_of_month_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@router.post("/track")
def track_action(
    body: TrackActionBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Track the current user's action (e.g. report_viewed, export). Recorded per user."""
    if body.action_type not in ("report_viewed", "export"):
        return {"ok": True}
    db.add(
        AuditLog(
            action_type=body.action_type,
            entity_type="profile",
            entity_id=current_user.id,
            performed_by=current_user.email,
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/metrics")
def get_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Activity metrics for the current user only: logins, reports_viewed, exports (this month)."""
    since = _start_of_month_utc()
    q = (
        db.query(AuditLog.action_type, func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= since, AuditLog.performed_by == current_user.email)
        .group_by(AuditLog.action_type)
    )
    rows = q.all()
    counts = {row[0]: row[1] for row in rows}
    return {
        "logins": counts.get("login", 0),
        "reports_viewed": counts.get("report_viewed", 0),
        "exports": counts.get("export", 0),
    }


@router.get("/activity")
def get_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
) -> list:
    """Recent activity for the current user only. Default: last 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.performed_by == current_user.email, AuditLog.timestamp >= since)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
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
