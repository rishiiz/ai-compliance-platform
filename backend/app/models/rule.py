"""Rule model."""

from datetime import datetime, timezone
import mongoengine as me
from app.models.policy import Policy


class Rule(me.Document):
    """Rule table."""
    meta = {'collection': 'rules'}

    policy_id = me.ReferenceField(Policy, required=True, reverse_delete_rule=me.CASCADE)
    rule_data = me.DictField(required=True)
    severity = me.StringField(max_length=64, required=True)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
