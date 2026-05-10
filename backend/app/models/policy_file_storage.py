"""Policy file storage: store uploaded policy files (ZIP contents) in the app database instead of Supabase."""

from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
import mongoengine as me


class PolicyFileStorage(me.Document):
    """
    Store policy file bytes in the app database.
    Used when Supabase Storage is not configured; enables full DB migration.
    """
    meta = {'collection': 'policy_file_storage'}

    storage_path = me.StringField(max_length=1024, required=True, unique=True)  # e.g. "zipname/file.pdf"
    content_type = me.StringField(max_length=255, required=True)
    data = me.BinaryField(required=True)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
