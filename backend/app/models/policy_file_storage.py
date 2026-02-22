"""Policy file storage: store uploaded policy files (ZIP contents) in the app database instead of Supabase."""

from sqlalchemy import Column, DateTime, Integer, LargeBinary, String
from sqlalchemy.sql import func

from app.database import Base

# LONGBLOB for MySQL (large PDFs), BYTEA for PostgreSQL
try:
    from sqlalchemy.dialects.mysql import LONGBLOB
    _DATA_TYPE = LargeBinary().with_variant(LONGBLOB(), "mysql")
except Exception:
    _DATA_TYPE = LargeBinary


class PolicyFileStorage(Base):
    """
    Store policy file bytes in the app database (MySQL LONGBLOB / PostgreSQL BYTEA).
    Used when Supabase Storage is not configured; enables full MySQL migration.
    """

    __tablename__ = "policy_file_storage"

    id = Column(Integer, primary_key=True, index=True)
    storage_path = Column(String(1024), nullable=False, index=True)  # e.g. "zipname/file.pdf"
    content_type = Column(String(255), nullable=False)
    data = Column(_DATA_TYPE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
