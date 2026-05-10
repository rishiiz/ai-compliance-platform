"""Reports export (PDF, CSV)."""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.audit_log import AuditLog
from app.models.policy import Policy
from app.models.rule import Rule
from app.models.scan_state import ScanState
from app.models.violation import Violation

router = APIRouter(prefix="/reports", tags=["reports"])


def _log_export() -> None:
    """Log an export action for profile metrics."""
    AuditLog(
        action_type="export",
        entity_type="report",
        entity_id="0",
        performed_by="user",
    ).save()


@router.get("/export/csv")
def export_csv() -> StreamingResponse:
    """Export compliance summary and violations as CSV."""
    _log_export()
    summary = Policy.objects().count(), Rule.objects().count(), Violation.objects().count()
    state = ScanState.objects().first()
    violations = Violation.objects().order_by("-detected_at").limit(1000)
    
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Compliance Report", datetime.now(timezone.utc).isoformat()])
    w.writerow(["Total policies", summary[0]])
    w.writerow(["Total rules", summary[1]])
    w.writerow(["Total violations", summary[2]])
    w.writerow(["Last scan", state.last_scan_timestamp.isoformat() if state and state.last_scan_timestamp else ""])
    w.writerow([])
    w.writerow(["Violation ID", "Rule ID", "Record ID", "Status", "Severity", "Detected at"])
    for v in violations:
        rule = Rule.objects(id=v.rule_id).first() if v.rule_id else None
        severity = rule.severity if rule else ""
        w.writerow([
            str(v.id),
            str(v.rule_id) if v.rule_id else "",
            v.record_id,
            v.status,
            severity,
            v.detected_at.isoformat() if v.detected_at else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compliance-report.csv"},
    )


def _build_pdf_bytes() -> bytes:
    """Build a compliance report PDF and return as bytes."""
    buf = io.BytesIO()
    width, height = letter
    c = canvas.Canvas(buf, pagesize=letter)
    y = height - inch

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(inch, y, "Compliance Report")
    y -= 0.4 * inch

    # Summary
    policies_count = Policy.objects().count()
    rules_count = Rule.objects().count()
    violations_count = Violation.objects().count()
    state = ScanState.objects().first()
    last_scan = ""
    if state and state.last_scan_timestamp:
        last_scan = state.last_scan_timestamp.strftime("%Y-%m-%d %H:%M UTC")

    c.setFont("Helvetica", 10)
    c.drawString(inch, y, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    y -= 0.25 * inch
    c.drawString(inch, y, f"Total policies: {policies_count}")
    y -= 0.25 * inch
    c.drawString(inch, y, f"Total rules: {rules_count}")
    y -= 0.25 * inch
    c.drawString(inch, y, f"Total violations: {violations_count}")
    y -= 0.25 * inch
    c.drawString(inch, y, f"Last scan: {last_scan}")
    y -= 0.5 * inch

    # Violations table header
    violations = Violation.objects().order_by("-detected_at").limit(500)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y, "Violations")
    y -= 0.3 * inch
    c.setFont("Helvetica", 8)
    c.drawString(inch, y, "ID")
    c.drawString(inch + 0.6 * inch, y, "Rule ID")
    c.drawString(inch + 1.2 * inch, y, "Record ID")
    c.drawString(inch + 2.2 * inch, y, "Status")
    c.drawString(inch + 2.8 * inch, y, "Severity")
    c.drawString(inch + 3.4 * inch, y, "Detected at")
    y -= 0.2 * inch

    for v in violations:
        if y < inch:
            c.showPage()
            y = height - inch
            c.setFont("Helvetica", 8)
        rule = Rule.objects(id=v.rule_id).first() if v.rule_id else None
        severity = rule.severity if rule else ""
        detected = v.detected_at.strftime("%Y-%m-%d %H:%M") if v.detected_at else ""
        c.drawString(inch, y, str(v.id)[:8] + "..")
        c.drawString(inch + 0.6 * inch, y, str(v.rule_id)[:8] + ".." if v.rule_id else "")
        c.drawString(inch + 1.2 * inch, y, (v.record_id or "")[:20])
        c.drawString(inch + 2.2 * inch, y, (v.status or "")[:12])
        c.drawString(inch + 2.8 * inch, y, (severity or "")[:8])
        c.drawString(inch + 3.4 * inch, y, detected[:16])
        y -= 0.2 * inch

    c.save()
    buf.seek(0)
    return buf.getvalue()


@router.get("/export/pdf")
def export_pdf() -> StreamingResponse:
    """Export compliance summary and violations as a real PDF."""
    _log_export()
    pdf_bytes = _build_pdf_bytes()
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=compliance-report.pdf"},
    )
