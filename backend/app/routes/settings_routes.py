"""App settings API (system, notifications, policy, user prefs)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppSettings

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_all_settings(db: Session) -> dict:
    """Return all settings as key-value dict."""
    rows = db.query(AppSettings).all()
    return {r.key: r.value for r in rows}


@router.get("")
def get_settings(db: Session = Depends(get_db)) -> dict:
    """Get all app settings (scan_frequency, severity_threshold, etc.)."""
    return _get_all_settings(db)


class SettingsUpdate(BaseModel):
    """Key-value pairs to update."""

    scan_frequency: str | None = None
    severity_threshold: int | None = None
    risk_threshold: int | None = None
    email_alerts: bool | None = None
    slack_webhook: str | None = None
    ai_model: str | None = None
    confidence_threshold: int | None = None
    policy_upload_max_file_size_mb: int | None = None
    policy_upload_max_per_hour: int | None = None


@router.patch("")
def update_settings(
    body: SettingsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """Update settings (only provided keys)."""
    updates = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        row = db.query(AppSettings).filter(AppSettings.key == key).first()
        str_val = str(value).lower() if isinstance(value, bool) else str(value)
        if row:
            row.value = str_val
        else:
            db.add(AppSettings(key=key, value=str_val))
    db.commit()
    return _get_all_settings(db)
