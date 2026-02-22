"""Scheduled job definitions."""

import logging
import time
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import AuditLog, ScanState
from app.models.scan_state import get_or_create_scan_state
from app.services.scan_service import run_scan

logger = logging.getLogger(__name__)


def run_compliance_scan() -> None:
    """
    Run the compliance scan every 24 hours.
    Updates the single ScanState row after every scan (success or failure).
    Logs execution in AuditLog.
    """
    logger.info("Scheduled scan started")
    db = SessionLocal()
    start = time.perf_counter()
    now = datetime.now(timezone.utc)
    try:
        result = run_scan(db)
        duration_seconds = time.perf_counter() - start

        # Maintain single active ScanState row
        state = get_or_create_scan_state(db)
        state.last_scan_timestamp = now
        state.last_scan_status = "success"
        state.total_violations_found = result["total_violations"]
        state.scan_duration_seconds = round(duration_seconds, 2)

        db.add(
            AuditLog(
                action_type="scan_run",
                entity_type="scan",
                entity_id=0,
                performed_by="scheduler",
                meta={
                    "last_scan_timestamp": now.isoformat(),
                    "rules_checked": result["rules_checked"],
                    "total_violations": result["total_violations"],
                    "resolved_count": result["resolved_count"],
                    "scan_duration_seconds": state.scan_duration_seconds,
                    "by_rule": result["by_rule"],
                },
            )
        )
        db.commit()
        logger.info(
            "Scheduled scan completed | total_violations=%s | resolved_count=%s | duration_seconds=%s",
            result["total_violations"],
            result["resolved_count"],
            round(duration_seconds, 2),
        )
    except Exception as e:
        duration_seconds = time.perf_counter() - start
        logger.error(
            "Scheduled scan failed | error=%s | duration_seconds=%s",
            str(e),
            round(duration_seconds, 2),
            exc_info=True,
        )
        db.rollback()

        # Update ScanState with failure
        state = get_or_create_scan_state(db)
        state.last_scan_timestamp = datetime.now(timezone.utc)
        state.last_scan_status = "failure"
        state.total_violations_found = 0
        state.scan_duration_seconds = round(duration_seconds, 2)

        db.add(
            AuditLog(
                action_type="scan_run",
                entity_type="scan",
                entity_id=0,
                performed_by="scheduler",
                meta={"error": str(e), "last_scan_status": "failure"},
            )
        )
        db.commit()
        raise
    finally:
        db.close()
