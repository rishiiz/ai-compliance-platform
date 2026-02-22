"""Scan state model: single row tracking last scan result."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_or_create_scan_state(db: "Session") -> "ScanState":
    """
    Return the single active ScanState row, creating it with defaults if none exists.
    Ensures only one row is ever maintained.
    """
    row = db.query(ScanState).first()
    if row is None:
        row = ScanState(
            last_scan_timestamp=None,
            last_scan_status=None,
            total_violations_found=0,
            scan_duration_seconds=None,
        )
        db.add(row)
        db.flush()
    return row


class ScanState(Base):
    """
    Single row tracking the last scan run.
    Only one active row is maintained; it is updated after every scan.
    """

    __tablename__ = "scan_state"
    __table_args__ = (
        CheckConstraint(
            "last_scan_status IN ('success', 'failure')",
            name="scan_state_status_check",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    last_scan_timestamp = Column(DateTime(timezone=True), nullable=True)
    last_scan_status = Column(String(16), nullable=True)  # success | failure
    total_violations_found = Column(Integer, nullable=False, server_default="0")
    scan_duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
