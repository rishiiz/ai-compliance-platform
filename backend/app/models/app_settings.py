"""App settings (key-value) for system, notifications, policy, user prefs."""

import mongoengine as me


class AppSettings(me.Document):
    """Key-value store for settings (scan_frequency, severity_threshold, etc.)."""
    meta = {'collection': 'app_settings'}

    key = me.StringField(max_length=128, unique=True, required=True)
    value = me.StringField(null=True)
