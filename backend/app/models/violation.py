"""Violation model."""

from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
import mongoengine as me
from app.models.rule import Rule


class Violation(me.Document):
    """Violation table."""
    meta = {
        'collection': 'violations',
        'indexes': [
            {'fields': ['rule_id', 'record_id'], 'unique': True}
        ]
    }

    rule_id = me.ReferenceField(Rule, required=True, reverse_delete_rule=me.CASCADE)
    record_id = me.StringField(max_length=255, required=True)
    evidence_snapshot = me.DictField(required=True)
    sql_query = me.StringField(required=True)
    explanation = me.StringField(required=True)
    suggested_remediation = me.StringField(null=True)
    policy_clause_text = me.StringField(null=True)
    status = me.StringField(max_length=20, default='pending', choices=('pending', 'approved', 'dismissed', 'resolved'))
    reviewer_notes = me.StringField(null=True)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    detected_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    resolved_at = me.DateTimeField(null=True)
