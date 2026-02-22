"""Rule model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Rule(Base):
    """Rule table."""

    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_data = Column(JSON, nullable=False)
    severity = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Many-to-one: Rule belongs to Policy
    policy = relationship("Policy", back_populates="rules")
    # One-to-many: one Rule has many Violations
    violations = relationship(
        "Violation",
        back_populates="rule",
        cascade="all, delete-orphan",
    )
