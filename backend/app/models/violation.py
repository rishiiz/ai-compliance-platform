"""Violation model."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Violation(Base):
    """Violation table."""

    __tablename__ = "violations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'dismissed', 'resolved')",
            name="violation_status_check",
        ),
        UniqueConstraint(
            "rule_id",
            "record_id",
            name="uq_violation_rule_record",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    record_id = Column(String(255), nullable=False)
    evidence_snapshot = Column(JSON, nullable=False)
    sql_query = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    suggested_remediation = Column(Text, nullable=True)
    policy_clause_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default=text("'pending'"))
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Many-to-one: Violation belongs to Rule
    rule = relationship("Rule", back_populates="violations")
