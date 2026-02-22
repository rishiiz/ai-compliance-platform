"""ZIP policy extraction and Supabase Storage upload service."""

import csv
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Allowed file extensions inside a ZIP
ALLOWED_EXTENSIONS = {".pdf", ".csv", ".txt"}
# Skip internal macOS / Windows metadata files
SKIP_PREFIXES = ("__MACOSX", ".", "_")


@dataclass
class ExtractedFile:
    """Represents a single file extracted from a ZIP archive."""
    filename: str
    file_type: str           # "pdf" | "csv" | "txt"
    text_content: str        # extracted plain text
    storage_path: str        # path inside Supabase Storage bucket
    storage_url: str         # public/signed URL (empty if storage disabled)
    raw_bytes: bytes = field(repr=False, default=b"")


def _upload_to_db_storage(storage_path: str, data: bytes, content_type: str) -> str:
    """
    Store file bytes in the app database (MySQL/PostgreSQL). Used when Supabase is not configured.
    Returns a relative URL path for download, e.g. /api/v1/files/download/123.
    """
    try:
        from app.database import SessionLocal
        from app.models import PolicyFileStorage

        session = SessionLocal()
        try:
            row = PolicyFileStorage(
                storage_path=storage_path[:1024],
                content_type=content_type,
                data=data,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return f"/files/download/{row.id}"
        finally:
            session.close()
    except Exception as e:
        logger.warning("DB storage upload failed for %s: %s", storage_path, e)
        return ""


def _upload_to_supabase_storage(storage_path: str, data: bytes, content_type: str) -> str:
    """
    Upload bytes to Supabase Storage via the REST API using httpx.
    Returns a signed URL (valid 7 days) or empty string on failure.
    """
    url = getattr(settings, "SUPABASE_URL", "")
    key = getattr(settings, "SUPABASE_KEY", "")
    bucket = getattr(settings, "SUPABASE_STORAGE_BUCKET", "policy-files")

    if not url or not key or "<your-" in url or "<your-" in key:
        return ""

    import httpx

    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    upload_url = f"{url.rstrip('/')}/storage/v1/object/{bucket}/{storage_path}"

    try:
        resp = httpx.put(upload_url, content=data, headers=headers, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Supabase Storage upload failed for %s: %s", storage_path, e)
        return ""

    sign_url = f"{url.rstrip('/')}/storage/v1/object/sign/{bucket}/{storage_path}"
    sign_headers = {"Authorization": f"Bearer {key}", "apikey": key, "Content-Type": "application/json"}
    try:
        sign_resp = httpx.post(sign_url, json={"expiresIn": 60 * 60 * 24 * 7}, headers=sign_headers, timeout=15)
        sign_resp.raise_for_status()
        data_resp = sign_resp.json()
        signed = data_resp.get("signedURL") or data_resp.get("signedUrl") or ""
        if signed and not signed.startswith("http"):
            signed = f"{url.rstrip('/')}{signed}"
        return signed
    except Exception as e:
        logger.warning("Supabase signed URL generation failed for %s: %s", storage_path, e)
        return f"{url.rstrip('/')}/storage/v1/object/public/{bucket}/{storage_path}"



def _extract_text_from_pdf(raw_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(pages).strip()
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""


def _extract_text_from_csv(raw_bytes: bytes) -> str:
    """Convert CSV bytes to readable key:value text for policy analysis."""
    try:
        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for i, row in enumerate(reader):
            row_parts = [f"{k}: {v}" for k, v in row.items() if v]
            rows.append(f"Row {i + 1}: " + " | ".join(row_parts))
        return "\n".join(rows).strip()
    except Exception as e:
        logger.warning("CSV text extraction failed: %s", e)
        return ""


def _extract_text_from_txt(raw_bytes: bytes) -> str:
    """Decode TXT bytes to plain text."""
    return raw_bytes.decode("utf-8", errors="replace").strip()


def extract_text_from_policy_file(raw_bytes: bytes, filename: str) -> str:
    """
    Extract text from a policy file (PDF, CSV, or TXT) given raw bytes and filename.
    Used by single-file policy upload. Returns extracted text or empty string on failure.
    """
    ext = (Path(filename).suffix or "").lower()
    if ext == ".pdf":
        return _extract_text_from_pdf(raw_bytes)
    if ext == ".csv":
        return _extract_text_from_csv(raw_bytes)
    if ext == ".txt":
        return _extract_text_from_txt(raw_bytes)
    logger.warning("Unsupported policy file extension: %s", ext)
    return ""


def _content_type_for_ext(ext: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".csv": "text/csv",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")


def extract_and_upload_zip(
    zip_bytes: bytes,
    zip_filename: str,
) -> list[ExtractedFile]:
    """
    Extract all supported files from a ZIP archive, upload each to Supabase Storage,
    and return a list of ExtractedFile objects with text content.

    Args:
        zip_bytes: Raw ZIP file bytes.
        zip_filename: Original filename of the ZIP (used for storage path prefix).

    Returns:
        List of ExtractedFile, one per supported file inside the zip.
    """
    results: list[ExtractedFile] = []
    zip_stem = Path(zip_filename).stem  # e.g. "my_policies" from "my_policies.zip"

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for member in zf.infolist():
                name = member.filename
                # Skip directories, hidden, or macOS metadata
                if member.is_dir():
                    continue
                basename = Path(name).name
                if any(basename.startswith(p) for p in SKIP_PREFIXES):
                    continue
                ext = Path(name).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    logger.debug("ZIP: skipping unsupported file %s", name)
                    continue

                try:
                    raw = zf.read(member.filename)
                except Exception as e:
                    logger.warning("ZIP: could not read member %s: %s", name, e)
                    continue

                # Extract text based on file type
                file_type = ext.lstrip(".")
                if file_type == "pdf":
                    text = _extract_text_from_pdf(raw)
                elif file_type == "csv":
                    text = _extract_text_from_csv(raw)
                else:
                    text = _extract_text_from_txt(raw)

                # Upload: Supabase if configured, else app database (MySQL/PostgreSQL)
                storage_path = f"{zip_stem}/{basename}"
                ct = _content_type_for_ext(ext)
                storage_url = _upload_to_supabase_storage(storage_path, raw, ct)
                if not storage_url:
                    storage_url = _upload_to_db_storage(storage_path, raw, ct)

                results.append(
                    ExtractedFile(
                        filename=basename,
                        file_type=file_type,
                        text_content=text,
                        storage_path=storage_path,
                        storage_url=storage_url,
                        raw_bytes=raw,
                    )
                )
                logger.info(
                    "ZIP extracted: file=%s type=%s chars=%s stored=%s",
                    basename,
                    file_type,
                    len(text),
                    bool(storage_url),
                )
    except zipfile.BadZipFile as e:
        raise ValueError(f"Invalid ZIP file: {e}") from e
    except Exception as e:
        logger.error("ZIP extraction failed: %s", e)
        raise

    return results
