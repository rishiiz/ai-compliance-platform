"""Dashboard API routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.models.policy import Policy
from app.models.rule import Rule
from app.models.scan_state import ScanState
from app.models.violation import Violation

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _trend_data_last_24h() -> list[dict]:
    """
    Build 24 hourly buckets for the last 24 hours from now (UTC).
    Each point: violations = count of violations detected in that hour,
    score = 100 - min(100, violations * 10) so 0 violations => 100.
    """
    now = datetime.now(timezone.utc)
    out = []
    for i in range(24):
        hour_start = now - timedelta(hours=24 - i)
        hour_end = hour_start + timedelta(hours=1)
        count = Violation.objects(
            detected_at__gte=hour_start,
            detected_at__lt=hour_end,
        ).count()
        score = max(0, 100 - min(100, count * 10))
        out.append({
            "date": hour_start.isoformat(),
            "score": score,
            "violations": count,
        })
    return out


def _violation_to_summary_item(v: Violation) -> dict:
    """Serialize a violation for recent_violations list."""
    rule = Rule.objects(id=v.rule_id).first()
    return {
        "id": str(v.id),
        "rule_id": str(v.rule_id),
        "record_id": v.record_id,
        "status": v.status,
        "severity": rule.severity if rule else None,
        "explanation": (v.explanation[:200] + "…") if v.explanation and len(v.explanation) > 200 else (v.explanation or ""),
        "detected_at": v.detected_at.isoformat() if v.detected_at else None,
    }


@router.get("/summary")
def get_dashboard_summary() -> dict:
    """
    Return dashboard summary: policy/rule/violation counts, pending and high-severity counts,
    and the last 5 violations.
    """
    total_policies = Policy.objects().count()
    total_rules = Rule.objects().count()
    total_violations = Violation.objects().count()
    pending_violations = Violation.objects(status="pending").count()
    
    # MongoEngine: Need to get high severity rule IDs first, then count violations for them
    high_sev_rules = Rule.objects(severity__iexact="high").only('id')
    high_sev_rule_ids = [str(r.id) for r in high_sev_rules]
    high_severity = Violation.objects(rule_id__in=high_sev_rule_ids).count()
    
    recent = Violation.objects().order_by("-detected_at", "-id").limit(5)
    recent_violations = [_violation_to_summary_item(v) for v in recent]

    scan_state = ScanState.objects().first()
    last_scan_timestamp = (
        scan_state.last_scan_timestamp.isoformat()
        if scan_state and scan_state.last_scan_timestamp
        else None
    )
    last_scan_status = scan_state.last_scan_status if scan_state else None
    total_violations_found = (
        scan_state.total_violations_found if scan_state else 0
    )
    scan_duration_seconds = (
        scan_state.scan_duration_seconds if scan_state else None
    )
    last_scan_created_at = (
        scan_state.created_at.isoformat()
        if scan_state and scan_state.created_at
        else None
    )

    trend_data = _trend_data_last_24h()

    return {
        "total_policies": total_policies,
        "total_rules": total_rules,
        "total_violations": total_violations,
        "pending_violations": pending_violations,
        "high_severity": high_severity,
        "recent_violations": recent_violations,
        "last_scan_timestamp": last_scan_timestamp,
        "last_scan_status": last_scan_status,
        "total_violations_found": total_violations_found,
        "scan_duration_seconds": scan_duration_seconds,
        "last_scan_created_at": last_scan_created_at,
        "trend_data": trend_data,
    }
