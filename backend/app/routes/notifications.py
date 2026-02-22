"""Notifications API (bell dropdown)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    limit: int = 50,
) -> list:
    """List notifications (e.g. for header dropdown)."""
    rows = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "type": r.type,
            "title": r.title,
            "body": r.body,
            "read": r.read,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Mark a notification as read."""
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    db.commit()
    db.refresh(n)
    return {"id": n.id, "read": True}
