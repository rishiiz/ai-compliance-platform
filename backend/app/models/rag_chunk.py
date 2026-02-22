"""RAG chunks stored in the app database when RAG_STORAGE_BACKEND=mysql."""

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.sql import func

from app.database import Base


class RagChunk(Base):
    """
    Policy text chunks and embeddings for RAG when using MySQL (or any app DB) instead of Chroma.
    embedding_json: JSON array of floats, e.g. "[0.1, -0.2, ...]".
    """

    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=False)  # JSON array of float
    policy_name = Column(Text, nullable=True)
    is_summary = Column(Integer, nullable=False, default=0)  # 0/1 for MySQL compatibility
    created_at = Column(DateTime(timezone=True), server_default=func.now())
