"""Reports export (PDF, CSV)."""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AuditLog, Policy, Rule, ScanState, Violation

router = APIRouter(prefix="/reports", tags=["reports"])


def _log_export(db: Session) -> None:
    """Log an export action for profile metrics."""
    db.add(
        AuditLog(
            action_type="export",
            entity_type="report",
            entity_id=0,
            performed_by="user",
        )
    )
    db.commit()


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    """Export compliance summary and violations as CSV."""
    _log_export(db)
    summary = db.query(Policy).count(), db.query(Rule).count(), db.query(Violation).count()
    state = db.query(ScanState).first()
    violations = (
        db.query(Violation)
        .options(joinedload(Violation.rule))
        .order_by(Violation.detected_at.desc())
        .limit(1000)
        .all()
    )
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
        severity = v.rule.severity if v.rule else ""
        w.writerow([
            v.id,
            v.rule_id,
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


def _build_pdf_bytes(db: Session) -> bytes:
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
    policies_count = db.query(Policy).count()
    rules_count = db.query(Rule).count()
    violations_count = db.query(Violation).count()
    state = db.query(ScanState).first()
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
    violations = (
        db.query(Violation)
        .options(joinedload(Violation.rule))
        .order_by(Violation.detected_at.desc())
        .limit(500)
        .all()
    )
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
        severity = v.rule.severity if v.rule else ""
        detected = v.detected_at.strftime("%Y-%m-%d %H:%M") if v.detected_at else ""
        c.drawString(inch, y, str(v.id))
        c.drawString(inch + 0.6 * inch, y, str(v.rule_id))
        c.drawString(inch + 1.2 * inch, y, (v.record_id or "")[:20])
        c.drawString(inch + 2.2 * inch, y, (v.status or "")[:12])
        c.drawString(inch + 2.8 * inch, y, (severity or "")[:8])
        c.drawString(inch + 3.4 * inch, y, detected[:16])
        y -= 0.2 * inch

    c.save()
    buf.seek(0)
    return buf.getvalue()


@router.get("/export/pdf")
def export_pdf(db: Session = Depends(get_db)) -> StreamingResponse:
    """Export compliance summary and violations as a real PDF."""
    _log_export(db)
    pdf_bytes = _build_pdf_bytes(db)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=compliance-report.pdf"},
    )
