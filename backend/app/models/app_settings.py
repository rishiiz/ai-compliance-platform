"""App settings (key-value) for system, notifications, policy, user prefs."""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AppSettings(Base):
    """Key-value store for settings (scan_frequency, severity_threshold, etc.)."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
