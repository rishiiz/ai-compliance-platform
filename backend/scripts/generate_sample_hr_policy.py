"""
Generate a second sample policy PDF (HR / Training) for demo variety.
Run from backend/: python scripts/generate_sample_hr_policy.py
Output: backend/sample-hr-policy.pdf
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def main() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    out_path = backend_dir / "sample-hr-policy.pdf"

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
    body_style = styles["Normal"]

    content = [
        Paragraph("HR & Employee Training Policy", title_style),
        Spacer(1, 0.3 * inch),
        Paragraph(
            "This policy sets requirements for employee training and compliance. "
            "Upload this PDF to demonstrate multiple policies and rule extraction.",
            body_style,
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("1. Mandatory Training Completion", styles["Heading2"]),
        Paragraph(
            "All employees must complete security and compliance training within 30 days of joining. "
            "The training_completed field must be true by the deadline. Managers are responsible for tracking completion.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("2. Background Checks", styles["Heading2"]),
        Paragraph(
            "Employees with access to customer data must have a completed background check on file. "
            "The background_check_status field must equal 'cleared' before access is granted.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("3. Access Review", styles["Heading2"]),
        Paragraph(
            "Access rights must be reviewed quarterly. Last access review date shall not be older than 90 days. "
            "Any employee whose access has not been reviewed within this period must be flagged.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("4. Data Handling Certification", styles["Heading2"]),
        Paragraph(
            "Personnel handling personal data must hold a valid data_handling_certified status. "
            "Certification expires after 12 months and must be renewed.",
            body_style,
        ),
    ]
    doc.build(content)
    print(f"Created: {out_path}")


if __name__ == "__main__":
    main()
