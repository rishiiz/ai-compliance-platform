"""Scan state model: single row tracking last scan result."""

from datetime import datetime, timezone
import mongoengine as me


def get_or_create_scan_state(db=None) -> "ScanState":
    """
    Return the single active ScanState row, creating it with defaults if none exists.
    Ensures only one row is ever maintained.
    """
    row = ScanState.objects().first()
    if row is None:
        row = ScanState(
            last_scan_timestamp=None,
            last_scan_status=None,
            total_violations_found=0,
            scan_duration_seconds=None,
        )
        row.save()
    return row


class ScanState(me.Document):
    """
    Single row tracking the last scan run.
    Only one active row is maintained; it is updated after every scan.
    """
    meta = {'collection': 'scan_state'}

    last_scan_timestamp = me.DateTimeField(null=True)
    last_scan_status = me.StringField(max_length=16, null=True, choices=('success', 'failure'))
    total_violations_found = me.IntField(default=0, required=True)
    scan_duration_seconds = me.FloatField(null=True)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
