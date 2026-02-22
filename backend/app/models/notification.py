"""Notification model for in-app notifications (bell dropdown)."""

from sqlalchemy import Column, Boolean, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    """In-app notifications (e.g. new violation, policy review due)."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(32), nullable=False)  # critical, warning, success, info
    title = Column(String(255), nullable=False)
    body = Column(String(1024), nullable=True)
    read = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
