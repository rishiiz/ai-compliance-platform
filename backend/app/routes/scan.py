"""Compliance scan API routes."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Rule
from app.models.scan_state import get_or_create_scan_state
from app.services.rule_engine import RuleExecutionError
from app.services.scan_service import run_scan as run_scan_service

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/run")
def run_scan(db: Session = Depends(get_db)) -> dict:
    """
    Run a full compliance scan: execute all rules, upsert violations (new or update),
    mark violations as resolved when no longer present. Updates the single ScanState row.
    Returns summary.
    """
    rules = db.query(Rule).all()
    if not rules:
        return {
            "message": "No rules to scan. Upload a policy first.",
            "rules_checked": 0,
            "total_violations": 0,
            "resolved_count": 0,
            "by_rule": [],
        }
    start = time.perf_counter()
    try:
        result = run_scan_service(db)
    except RuleExecutionError as e:
        msg = str(e)
        # When no external DB, return 200 with zero results so UI shows message instead of "Scan failed"
        if "No external database" in msg or "external database connected" in msg.lower():
            return {
                "message": "No external database connected. Connect a company database in Settings → Database to run compliance rules.",
                "rules_checked": 0,
                "total_violations": 0,
                "resolved_count": 0,
                "by_rule": [],
                "scan_duration_seconds": 0,
            }
        # When company DB is missing tables/columns that rules expect, return 200 with a clear message
        if "does not exist" in msg.lower() or "relation" in msg.lower() or "column" in msg.lower():
            return {
                "message": "Your company database is missing tables or columns that the scan rules expect. Rules were extracted from your policy PDFs and reference tables (e.g. policy_docs) with columns (e.g. compliance_verified, retention_period_years, dpa_signed). Create these tables in your company database (e.g. in pgAdmin) to run scans, or the scan will fail.",
                "rules_checked": 0,
                "total_violations": 0,
                "resolved_count": 0,
                "by_rule": [],
                "scan_duration_seconds": 0,
            }
        raise HTTPException(status_code=422, detail=msg) from e
    duration_seconds = time.perf_counter() - start
    now = datetime.now(timezone.utc)

    # Update single ScanState row after every scan
    state = get_or_create_scan_state(db)
    state.last_scan_timestamp = now
    state.last_scan_status = "success"
    state.total_violations_found = result["total_violations"]
    state.scan_duration_seconds = round(duration_seconds, 2)

    # Store scan metrics in AuditLog
    db.add(
        AuditLog(
            action_type="scan_run",
            entity_type="scan",
            entity_id=0,
            performed_by="api",
            meta={
                "last_scan_timestamp": now.isoformat(),
                "rules_checked": result["rules_checked"],
                "total_violations": result["total_violations"],
                "resolved_count": result["resolved_count"],
                "scan_duration_seconds": round(duration_seconds, 2),
                "by_rule": result["by_rule"],
            },
        )
    )

    db.commit()
    return {
        "message": "Scan completed.",
        "rules_checked": result["rules_checked"],
        "total_violations": result["total_violations"],
        "resolved_count": result["resolved_count"],
        "by_rule": result["by_rule"],
        "scan_duration_seconds": round(duration_seconds, 2),
    }
