"""Audit log model."""

from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from app.database import Base


class AuditLog(Base):
    """Audit log table for tracking policy, rule, and violation actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(64), nullable=False)
    entity_type = Column(String(32), nullable=False)  # policy, rule, violation
    entity_id = Column(Integer, nullable=False)
    performed_by = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    meta = Column(JSON, nullable=True)  # JSON works on SQLite and PostgreSQL; "metadata" is reserved by Declarative
