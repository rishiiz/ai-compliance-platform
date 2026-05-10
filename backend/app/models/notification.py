"""Notification model for in-app notifications (bell dropdown)."""

from datetime import datetime, timezone
import mongoengine as me


class Notification(me.Document):
    """In-app notifications (e.g. new violation, policy review due)."""
    meta = {'collection': 'notifications'}

    type = me.StringField(max_length=32, required=True)  # critical, warning, success, info
    title = me.StringField(max_length=255, required=True)
    body = me.StringField(max_length=1024, null=True)
    read = me.BooleanField(default=False)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
