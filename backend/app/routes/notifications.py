"""Notifications API (bell dropdown)."""

from fastapi import APIRouter, HTTPException

from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    limit: int = 50,
) -> list:
    """List notifications (e.g. for header dropdown)."""
    rows = Notification.objects().order_by("-created_at").limit(limit)
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
    notification_id: str,
) -> dict:
    """Mark a notification as read."""
    n = Notification.objects(id=notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    n.save()
    return {"id": str(n.id), "read": True}
