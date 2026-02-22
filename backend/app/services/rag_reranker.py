"""
Optional re-ranker for RAG: re-rank top chunks with a lightweight cross-encoder.
Disabled by default (RAG_USE_RERANKER=false). Requires sentence-transformers with cross-encoder support.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model: Any = None


def _get_model() -> Any:
    global _model
    if _model is None:
        try:
            from sentence_transformers import CrossEncoder
            _model = CrossEncoder(_CROSS_ENCODER_MODEL)
        except Exception as e:
            logger.warning("RAG re-ranker model load failed: %s", e)
            raise
    return _model


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Re-rank chunks by relevance to query using a cross-encoder.
    chunks: list of { "text", "score", ... }. Returns top_n chunks in order of cross-encoder score.
    """
    if not chunks or top_n <= 0:
        return chunks
    model = _get_model()
    pairs = [(query, c.get("text", "")) for c in chunks]
    scores = model.predict(pairs)
    indexed = list(zip(scores, chunks, range(len(chunks))))
    indexed.sort(key=lambda x: (-float(x[0]), x[2]))
    out = []
    for s, chunk, _ in indexed[:top_n]:
        c = dict(chunk)
        c["score"] = float(s)
        out.append(c)
    return out
