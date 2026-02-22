"""
Generate a sample rule PDF for testing the RAG model and Ask policy.
Run from backend/: python scripts/generate_sample_rules_test.py
Output: backend/sample-rules-test.pdf
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def main() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    out_path = backend_dir / "sample-rules-test.pdf"

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
        Paragraph("Compliance Rules & RAG Test Policy", title_style),
        Spacer(1, 0.3 * inch),
        Paragraph(
            "This document is for testing the RAG model and Ask policy. "
            "Upload it, index it, then ask questions such as: What is the data retention period? "
            "When must training be completed? What about DPAs?",
            body_style,
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("1. Data Retention Period", styles["Heading2"]),
        Paragraph(
            "The data retention period for personal data and transaction records is 5 years from the date of last activity. "
            "After 5 years, data must be securely deleted unless a longer retention is required by applicable law. "
            "Audit logs must be retained for at least 7 years.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("2. Training Completion Deadline", styles["Heading2"]),
        Paragraph(
            "Security and compliance training must be completed within 90 days of hire or role change. "
            "When must training be completed? No later than 90 days after the employee start date. "
            "Annual refresher training is required and must be completed by December 31 of each year.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("3. Data Processing Agreements (DPAs)", styles["Heading2"]),
        Paragraph(
            "Third-party processors must sign a Data Processing Agreement (DPA) before any personal data is shared. "
            "DPAs must include standard contractual clauses where required. Sub-processors require prior written approval. "
            "A register of processors and DPAs must be maintained.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("4. Encryption Requirements", styles["Heading2"]),
        Paragraph(
            "All personal data must be encrypted at rest using AES-256 or equivalent. "
            "Data in transit must use TLS 1.2 or higher. Keys must be managed in a dedicated key management system.",
            body_style,
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("5. Incident Response", styles["Heading2"]),
        Paragraph(
            "Data breaches must be reported to the compliance officer within 24 hours of discovery. "
            "Regulatory notification (e.g. to a supervisory authority) must occur within 72 hours where required by law.",
            body_style,
        ),
    ]
    doc.build(content)
    print(f"Created: {out_path}")
    print("Upload this PDF in the app, then use Ask policy to test questions like:")
    print("  - What is the data retention period?")
    print("  - When must training be completed?")
    print("  - What about DPAs?")


if __name__ == "__main__":
    main()
