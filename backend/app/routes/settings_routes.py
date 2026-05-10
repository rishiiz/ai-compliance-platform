"""App settings API (system, notifications, policy, user prefs)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.app_settings import AppSettings

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_all_settings() -> dict:
    """Return all settings as key-value dict."""
    rows = AppSettings.objects()
    return {r.key: r.value for r in rows}


@router.get("")
def get_settings() -> dict:
    """Get all app settings (scan_frequency, severity_threshold, etc.)."""
    return _get_all_settings()


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
) -> dict:
    """Update settings (only provided keys)."""
    updates = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        row = AppSettings.objects(key=key).first()
        str_val = str(value).lower() if isinstance(value, bool) else str(value)
        if row:
            row.value = str_val
            row.save()
        else:
            AppSettings(key=key, value=str_val).save()
    return _get_all_settings()
