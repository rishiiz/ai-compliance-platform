"""
Generate a sample policy PDF for testing the policy upload flow.
Run from backend/: python scripts/generate_sample_policy.py
Output: backend/sample-policy.pdf
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def main() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    out_path = backend_dir / "sample-policy.pdf"

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
        Paragraph("Data Protection & Compliance Policy", title_style),
        Spacer(1, 0.3 * inch),
        Paragraph(
            "This document defines policy rules for data handling and compliance. "
            "Use this PDF to test policy upload and rule extraction in the AI Compliance Platform.",
            body_style,
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("1. Data Encryption", styles["Heading2"]),
        Paragraph(
            "All personal data and sensitive information MUST be encrypted at rest and in transit. "
            "Encryption must use industry-standard algorithms (e.g. AES-256).",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("2. Retention Period", styles["Heading2"]),
        Paragraph(
            "Retention period for customer data shall not exceed 7 years after the last transaction, "
            "unless a longer period is required by law.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("3. Third-Party Processors", styles["Heading2"]),
        Paragraph(
            "Third-party data processors must sign a Data Processing Agreement (DPA) before handling "
            "any personal data. Sub-processors require prior written approval.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("4. Access Control", styles["Heading2"]),
        Paragraph(
            "Access to production data is restricted to authorized personnel only. "
            "Role-based access control (RBAC) must be enforced.",
            body_style,
        ),
    ]
    doc.build(content)
    print(f"Created: {out_path}")


if __name__ == "__main__":
    main()
