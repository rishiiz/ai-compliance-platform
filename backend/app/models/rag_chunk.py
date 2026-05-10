"""RAG chunks stored in the app database when RAG_STORAGE_BACKEND=mysql."""

from datetime import datetime, timezone
import mongoengine as me


class RagChunk(me.Document):
    """
    Policy text chunks and embeddings for RAG when using MongoDB (or any app DB) instead of Chroma.
    embedding_json: JSON array of floats, e.g. "[0.1, -0.2, ...]".
    """
    meta = {'collection': 'rag_chunks'}

    policy_id = me.StringField(required=True)
    chunk_index = me.IntField(required=True)
    content = me.StringField(required=True)
    embedding_json = me.StringField(required=True)  # JSON array of float
    policy_name = me.StringField(null=True)
    is_summary = me.IntField(default=0, required=True)  # 0/1
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
