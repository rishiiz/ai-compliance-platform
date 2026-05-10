"""Audit log model."""

from datetime import datetime, timezone
import mongoengine as me


class AuditLog(me.Document):
    """Audit log table for tracking policy, rule, and violation actions."""
    meta = {'collection': 'audit_logs'}

    action_type = me.StringField(max_length=64, required=True)
    entity_type = me.StringField(max_length=32, required=True)  # policy, rule, violation
    entity_id = me.StringField(required=True)  # Using StringField since ObjectId translates to string
    performed_by = me.StringField(max_length=255, null=True)
    timestamp = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    meta_data = me.DictField(null=True, db_field="meta")  # meta is reserved in mongoengine Document
