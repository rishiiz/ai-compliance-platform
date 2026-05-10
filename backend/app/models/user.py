"""User model for auth, profile, 2FA, and user management."""

from datetime import datetime, timezone
import mongoengine as me


class User(me.Document):
    """Users for login, profile, and 2FA."""
    meta = {'collection': 'users'}

    email = me.StringField(max_length=255, unique=True, required=True)
    name = me.StringField(max_length=255, required=True)
    role = me.StringField(max_length=64, required=True)  # Admin, Compliance Officer, Viewer
    department = me.StringField(max_length=128, null=True)
    password_hash = me.StringField(max_length=255, null=True)  # optional for demo
    two_fa_secret = me.StringField(max_length=64, null=True)
    two_fa_enabled = me.BooleanField(default=False)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
