"""
Generate a one-page PDF explainer for judges: What are Violations?
Run from backend/: python scripts/generate_violations_explainer_pdf.py
Output: backend/Violations_Explainer.pdf
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def main() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    out_path = backend_dir / "Violations_Explainer.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=12,
    )
    body_style = styles["Normal"]

    content = [
        Paragraph("What Are Violations? (For Judges)", title_style),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "In this platform, <b>Violations</b> are <b>records in your connected company database</b> that break the compliance rules extracted from your policy PDFs. This one-pager explains what the Violations section shows and how it fits into the demo.",
            body_style,
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("How violations are created", h2_style),
        Paragraph(
            "1. You upload policy PDFs (e.g. Data Protection Policy, HR Policy). The system extracts structured compliance rules (entity, field, condition, severity). "
            "2. You connect a company database (Settings → Database). "
            "3. You run a compliance scan (Dashboard → Run scan now). The engine compiles each rule to SQL and runs it against the database. "
            "4. Any row that fails a rule is stored as a <b>violation</b>. Each violation has: the rule (policy clause), the record that failed, an AI-generated explanation, and a snapshot of the data (evidence).",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("What each violation shows", h2_style),
        Paragraph(
            "<b>Clause / Rule:</b> The policy rule that was violated (e.g. \"All personal data must be encrypted at rest\"). "
            "<b>Severity:</b> Critical, High, or Medium. "
            "<b>Status:</b> Pending (needs review), Approved, or Dismissed. "
            "<b>Policy name:</b> Which policy PDF the rule came from. "
            "<b>Evidence:</b> The actual data from the database row that failed the rule. "
            "<b>AI Explanation:</b> A short, human-readable explanation of why this record violates the rule. "
            "<b>Affected resource:</b> Identifier of the record (e.g. row id).",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Human oversight", h2_style),
        Paragraph(
            "Reviewers can approve or dismiss each violation and add notes. Every status change is logged in an audit trail (per violation) for regulators. The Violations list can be filtered by severity and searched.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Why the list might be empty", h2_style),
        Paragraph(
            "If no database is connected, or no scan has been run, or no database rows currently fail any rule, the Violations section will show \"No violations yet.\" To see violations in the demo: connect a PostgreSQL database with tables that match your rules (e.g. employees with training_completed, date_of_joining), then run a scan from the Dashboard.",
            body_style,
        ),
    ]
    doc.build(content)
    print(f"Created: {out_path}")


if __name__ == "__main__":
    main()
