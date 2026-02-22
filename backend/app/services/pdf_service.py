"""PDF text extraction service using PyMuPDF."""

from pathlib import Path

import fitz


class PDFExtractionError(Exception):
    """Raised when PDF text extraction fails."""

    pass


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract full text from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Full text content of the PDF, all pages concatenated.

    Raises:
        FileNotFoundError: If the file does not exist.
        PDFExtractionError: If the file is not a valid PDF or extraction fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if not path.is_file():
        raise PDFExtractionError(f"Path is not a file: {file_path}")

    doc = None
    try:
        doc = fitz.open(file_path)
        parts = []
        for page in doc:
            parts.append(page.get_text("text"))
        return "\n".join(parts)
    except (fitz.FileDataError, RuntimeError) as e:
        raise PDFExtractionError(f"Invalid or corrupted PDF: {file_path}") from e
    except Exception as e:
        raise PDFExtractionError(f"Failed to extract text from PDF: {e}") from e
    finally:
        if doc is not None:
            doc.close()
