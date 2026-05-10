"""
RAG storage backend using the app database (MongoDB).
Used when RAG_STORAGE_BACKEND=mysql (now maps to MongoDB). Stores chunks and embeddings in rag_chunks collection.
"""

import json
import logging
from typing import Any

from app.config import settings
from app.models.rag_chunk import RagChunk

logger = logging.getLogger(__name__)

# Max chunks to load for similarity search (avoid OOM on huge DBs)
RAG_MYSQL_RETRIEVE_LIMIT = 10000


def _embedding_fn():
    """Lazy import to avoid circular import."""
    from app.services.rag_service import _make_embedding_function
    return _make_embedding_function()


def _chunk_policy_text(extracted_text: str, policy_id: str, policy_name: str):
    from app.services.rag_service import chunk_policy_text
    return chunk_policy_text(extracted_text, policy_id, policy_name)


def _embed_query(query: str) -> list[float] | None:
    from app.services.rag_service import _embed_query_with_cache
    return _embed_query_with_cache(query)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def index_policy_chunks_mysql(
    extracted_text: str,
    policy_id: str,
    policy_name: str,
) -> bool:
    """Chunk, embed, and store in rag_chunks. Delete existing chunks for this policy first."""
    try:
        ef = _embedding_fn()
        chunks_with_meta = _chunk_policy_text(extracted_text, policy_id, policy_name)
        if not chunks_with_meta:
            return False
        documents = [c["text"] for c in chunks_with_meta]
        metadatas = [c["metadata"] for c in chunks_with_meta]
        embeddings = ef(documents)
        if not embeddings:
            return False
        
        RagChunk.objects(policy_id=str(policy_id)).delete()
        for i, (doc, meta, emb) in enumerate(zip(documents, metadatas, embeddings)):
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            else:
                emb = list(emb)
            RagChunk(
                policy_id=str(policy_id),
                chunk_index=meta.get("chunk_index", i),
                content=doc,
                embedding_json=json.dumps(emb),
                policy_name=(meta.get("policy_name") or "")[:500],
                is_summary=1 if meta.get("is_summary") else 0,
            ).save()
        logger.info("RAG (MongoDB) indexed %s chunks for policy_id=%s", len(documents), policy_id)
        return True
    except Exception as e:
        logger.warning("RAG (MongoDB) index failed for policy_id=%s: %s", policy_id, e)
        return False


def retrieve_mysql(
    query: str,
    top_k: int | None = None,
    policy_id: str | None = None,
    use_summaries_only: bool = False,
) -> list[dict]:
    """Load chunks from DB, compute similarity, return top_k."""
    query = (query or "").strip()
    if not query:
        return []
    query_emb = _embed_query(query)
    if not query_emb:
        return []
    k = top_k if top_k is not None else getattr(settings, "RAG_TOP_K", 5)
    k = min(k, getattr(settings, "RAG_TOP_K_MAX", 10))
    
    q = RagChunk.objects().order_by('id')
    if policy_id is not None:
        q = q.filter(policy_id=str(policy_id))
    if use_summaries_only and getattr(settings, "RAG_USE_SUMMARIES", False):
        q = q.filter(is_summary=1)
    rows = q.limit(RAG_MYSQL_RETRIEVE_LIMIT)
    scored = []
    min_sim = getattr(settings, "RAG_MIN_SIMILARITY", 0.75)
    for row in rows:
        try:
            emb = json.loads(row.embedding_json)
        except Exception:
            continue
        score = _cosine_similarity(query_emb, emb)
        if score >= min_sim:
            scored.append({
                "text": row.content,
                "policy_id": row.policy_id,
                "chunk_index": row.chunk_index,
                "policy_name": row.policy_name or "",
                "score": score,
            })
    scored.sort(key=lambda x: -x["score"])
    return scored[:k]


def delete_policy_from_index_mysql(policy_id: str) -> None:
    try:
        RagChunk.objects(policy_id=str(policy_id)).delete()
        logger.info("RAG (MongoDB) deleted chunks for policy_id=%s", policy_id)
    except Exception as e:
        logger.warning("RAG (MongoDB) delete failed for policy_id=%s: %s", policy_id, e)


def get_indexed_count_mysql() -> int:
    try:
        return RagChunk.objects().count()
    except Exception as e:
        logger.debug("RAG (MongoDB) count failed: %s", e)
        return 0
