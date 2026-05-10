"""RAG service: chunk policy text, embed (OpenAI or local sentence-transformers), store and query Chroma."""

import logging
import re
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Common legal boilerplate phrases to shorten or remove when repeated (optional)
_DEFAULT_BOILERPLATE_PATTERNS = [
    r"\bthe foregoing\b",
    r"\bwithout limiting the foregoing\b",
    r"\bsubject to (the )?terms (and conditions )?of (this )?(policy|agreement|document)\b",
]

# Last error from Chroma init, so get_rag_status() can surface it in the UI
_last_rag_init_error: str | None = None

COLLECTION_NAME = "policy_chunks"
CHARS_PER_TOKEN = 4  # fallback when tiktoken not used
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _use_openai_embeddings() -> bool:
    """True if we should use OpenAI for embeddings (key set and not placeholder)."""
    use_local = getattr(settings, "USE_LOCAL_EMBEDDINGS", False)
    if use_local:
        return False
    key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    return bool(key) and "your_openai_key_here" not in key.lower()


def _is_rag_available() -> bool:
    """True if RAG is enabled and we have embeddings (OpenAI, sentence-transformers, or ONNX) and Chroma path."""
    if not getattr(settings, "RAG_ENABLED", True):
        return False
    if _use_openai_embeddings():
        path = _chroma_path()
        return bool(path)
    try:
        import sentence_transformers  # noqa: F401
        path = _chroma_path()
        return bool(path)
    except ImportError:
        pass
    try:
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
        path = _chroma_path()
        return bool(path)
    except ImportError:
        return False


def get_rag_status() -> dict:
    """Return { "available": bool, "reason": str } for debugging and UI hints."""
    if not getattr(settings, "RAG_ENABLED", True):
        return {"available": False, "reason": "RAG is disabled (RAG_ENABLED=false)."}
    backend = (getattr(settings, "RAG_STORAGE_BACKEND", None) or "chroma").strip().lower()
    if backend == "mysql":
        try:
            from app.services.rag_storage_mysql import get_indexed_count_mysql
            get_indexed_count_mysql()
            return {"available": True, "reason": "RAG storage: MySQL (app database)."}
        except Exception as e:
            return {"available": False, "reason": f"RAG (MySQL) unavailable: {e}. Ensure app database is migrated (rag_chunks table exists)."}
    try:
        import chromadb  # noqa: F401
    except ImportError as e:
        return {"available": False, "reason": f"chromadb is not installed. Run in backend folder: pip install -r requirements.txt. Error: {e}"}
    if _use_openai_embeddings():
        key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
        if not key:
            return {"available": False, "reason": "OPENAI_API_KEY is not set in backend .env."}
        if "your_openai_key_here" in key.lower():
            return {"available": False, "reason": "OPENAI_API_KEY is still the placeholder. Set a real key or set USE_LOCAL_EMBEDDINGS=true to use local embeddings."}
    else:
        try:
            import sentence_transformers  # noqa: F401
        except ImportError as e:
            return {"available": False, "reason": f"Local embeddings require sentence-transformers. Run: pip install sentence-transformers. Error: {e}"}
    try:
        pair = _get_client_and_collection()
        if not pair:
            reason = _last_rag_init_error or "Chroma could not be initialized."
            return {"available": False, "reason": f"{reason} Check dependencies (pip install -r requirements.txt) and restart the backend."}
        return {"available": True, "reason": ""}
    except Exception as e:
        return {"available": False, "reason": f"RAG init failed: {e}. Install dependencies: pip install -r requirements.txt. Restart the backend."}


def _chroma_path() -> str:
    """Resolved Chroma persistence path (default backend/data/chroma when empty)."""
    path = (getattr(settings, "RAG_CHROMA_PATH", None) or "").strip()
    if path:
        return path
    backend_root = Path(__file__).resolve().parent.parent.parent
    return str(backend_root / "data" / "chroma")


def _make_embedding_function() -> Any:
    """Return Chroma embedding function: OpenAI if key set, else local (SentenceTransformer or ONNX fallback)."""
    import chromadb.utils.embedding_functions as ef_module

    if _use_openai_embeddings():
        return ef_module.OpenAIEmbeddingFunction(
            api_key=settings.OPENAI_API_KEY,
            model_name="text-embedding-3-small",
        )
    model_name = getattr(settings, "LOCAL_EMBEDDING_MODEL", None) or LOCAL_EMBEDDING_MODEL
    try:
        return ef_module.SentenceTransformerEmbeddingFunction(model_name=model_name)
    except Exception as e:
        logger.info("SentenceTransformer embedding unavailable (%s), trying ONNX fallback.", e)
        try:
            return ef_module.ONNXMiniLM_L6_V2()
        except Exception as onnx_e:
            logger.warning("ONNX embedding also failed: %s", onnx_e)
            raise


def _get_client_and_collection() -> tuple[Any, Any] | None:
    """Lazy-init Chroma client and collection. Returns (client, collection) or None if unavailable."""
    global _last_rag_init_error
    _last_rag_init_error = None
    if not _is_rag_available():
        return None
    try:
        import chromadb

        path = _chroma_path()
        Path(path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=path)
        ef = _make_embedding_function()
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
            metadata={"description": "Policy text chunks for RAG"},
        )
        return (client, collection)
    except Exception as e:
        err_msg = str(e).lower()
        # Collection was created with a different embedding function (e.g. openai vs sentence_transformer). Delete and recreate.
        if "embedding function" in err_msg and ("conflict" in err_msg or "already exists" in err_msg):
            try:
                client.delete_collection(COLLECTION_NAME)
                logger.info("RAG: deleted existing collection (embedding function conflict), recreating with current embedding.")
                collection = client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    embedding_function=ef,
                    metadata={"description": "Policy text chunks for RAG"},
                )
                return (client, collection)
            except Exception as e2:
                _last_rag_init_error = str(e2)
                logger.warning("RAG Chroma init failed after collection reset: %s", e2)
                return None
        _last_rag_init_error = str(e)
        logger.warning("RAG Chroma init failed: %s", e)
        return None


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single space and strip."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _remove_page_numbers(text: str) -> str:
    """Remove common page number patterns (e.g. 'Page 5', '5 / 12', footer numbers)."""
    text = re.sub(r"\bpage\s+\d+\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\d+\s*/\s*\d+", "", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    return _normalize_whitespace(text)


def _remove_repeated_lines(text: str, min_occurrences: int = 2) -> str:
    """Remove lines that appear repeatedly (headers/footers)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) <= 1:
        return text
    from collections import Counter
    counts = Counter(lines)
    repeated = {ln for ln, c in counts.items() if c >= min_occurrences and len(ln) < 200}
    if not repeated:
        return text
    new_lines = [ln for ln in lines if ln not in repeated]
    return "\n".join(new_lines)


def _shorten_boilerplate(text: str) -> str:
    """Shorten or remove common legal boilerplate (configurable)."""
    for pat in _DEFAULT_BOILERPLATE_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    return _normalize_whitespace(text)


def _extract_rule_kv_snippet(text: str) -> str | None:
    """
    If text looks like a rule (deadline, retention, etc.), return a short key-value snippet.
    Returns None if not detected. Used only when RAG_NORMALIZE_RULES_TO_KV is True.
    """
    # Simple patterns: "within X days", "X years retention", "not exceed X"
    m = re.search(r"within\s+(\d+)\s*(day|days|month|months|year|years)", text, re.IGNORECASE)
    if m:
        return f"deadline: {m.group(1)} {m.group(2)}"
    m = re.search(r"retention\s+(?:of|period)\s*(?:of\s*)?(\d+)\s*(day|days|month|months|year|years)", text, re.IGNORECASE)
    if m:
        return f"retention: {m.group(1)} {m.group(2)}"
    m = re.search(r"(?:shall\s+not\s+exceed|not\s+exceed)\s+(\d+)\s*(day|days|month|months|year|years)", text, re.IGNORECASE)
    if m:
        return f"max: {m.group(1)} {m.group(2)}"
    return None


def prepare_text_for_rag(extracted_text: str) -> str:
    """
    Clean and optionally normalize policy text before chunking (semantic compression).
    Removes repeated headers/footers, page numbers, normalizes whitespace; optionally shortens boilerplate.
    """
    if not (extracted_text or "").strip():
        return ""
    text = (extracted_text or "").strip()
    if not getattr(settings, "RAG_SEMANTIC_COMPRESSION", True):
        return _normalize_whitespace(text)
    text = _normalize_whitespace(text)
    text = _remove_page_numbers(text)
    text = _remove_repeated_lines(text, min_occurrences=2)
    text = _shorten_boilerplate(text)
    return text


def _clean_chunk_text(chunk_text: str) -> str:
    """Light clean applied to each chunk before storing (whitespace + page numbers)."""
    if not chunk_text:
        return ""
    t = _normalize_whitespace(chunk_text)
    t = _remove_page_numbers(t)
    return t


def _chunk_by_tokens(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text into chunks by token count with overlap. Uses tiktoken if available else char heuristic."""
    text = (text or "").strip()
    if not text:
        return []
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        chunks = []
        step = max(1, max_tokens - overlap_tokens)
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = enc.decode(chunk_tokens)
            if chunk_text.strip():
                chunks.append(chunk_text.strip())
            start = end - overlap_tokens
        return chunks
    except Exception:
        step_chars = max(1, (max_tokens - overlap_tokens) * CHARS_PER_TOKEN)
        overlap_chars = overlap_tokens * CHARS_PER_TOKEN
        chunk_size = max_tokens * CHARS_PER_TOKEN
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap_chars
        return chunks


def chunk_policy_text(
    extracted_text: str,
    policy_id: str,
    policy_name: str,
) -> list[dict]:
    """
    Chunk policy text and return list of { "text", "metadata": { "policy_id", "chunk_index", "policy_name" } }.
    Respects RAG_MAX_CHUNKS_PER_POLICY. Applies semantic compression (prepare_text_for_rag) before chunking.
    """
    max_chunks = getattr(settings, "RAG_MAX_CHUNKS_PER_POLICY", 200)
    chunk_tokens = getattr(settings, "RAG_CHUNK_TOKENS", 512)
    overlap_tokens = getattr(settings, "RAG_CHUNK_OVERLAP_TOKENS", 50)
    prepared = prepare_text_for_rag(extracted_text or "")
    raw = _chunk_by_tokens(prepared, chunk_tokens, overlap_tokens)
    limited = raw[:max_chunks]
    if len(raw) > max_chunks:
        logger.info("RAG: truncated policy text to %s chunks (policy_id=%s)", max_chunks, policy_id)
    normalize_kv = getattr(settings, "RAG_NORMALIZE_RULES_TO_KV", False)
    out = []
    for i, t in enumerate(limited):
        chunk_text = _clean_chunk_text(t)
        if normalize_kv:
            kv = _extract_rule_kv_snippet(chunk_text)
            if kv:
                chunk_text = f"[{kv}] {chunk_text}"
        out.append({
            "text": chunk_text,
            "metadata": {
                "policy_id": policy_id,
                "chunk_index": i,
                "policy_name": (policy_name or "")[:500],
                "is_summary": False,
            },
        })
    return out


def index_policy_chunks(
    extracted_text: str,
    policy_id: str,
    policy_name: str,
) -> bool:
    """
    Chunk policy text, embed, and add to RAG storage (Chroma or MySQL per RAG_STORAGE_BACKEND).
    Removes existing chunks for this policy_id before adding (overwrite on re-upload).

    Returns True if indexing was attempted and succeeded, False otherwise.
    """
    backend = (getattr(settings, "RAG_STORAGE_BACKEND", None) or "chroma").strip().lower()
    if backend == "mysql":
        from app.services.rag_storage_mysql import index_policy_chunks_mysql
        return index_policy_chunks_mysql(extracted_text, policy_id, policy_name)
    pair = _get_client_and_collection()
    if not pair:
        return False
    _client, collection = pair
    try:
        collection.delete(where={"policy_id": policy_id})
    except Exception as e:
        logger.debug("RAG delete existing chunks for policy_id=%s: %s", policy_id, e)
    chunks_with_meta = chunk_policy_text(extracted_text, policy_id, policy_name)
    if not chunks_with_meta:
        return False
    ids = [f"policy_{policy_id}_chunk_{c['metadata']['chunk_index']}" for c in chunks_with_meta]
    documents = [c["text"] for c in chunks_with_meta]
    metadatas = [c["metadata"] for c in chunks_with_meta]
    try:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info("RAG indexed %s chunks for policy_id=%s", len(documents), policy_id)
    except Exception as e:
        logger.warning("RAG index failed for policy_id=%s: %s", policy_id, e)
        return False
    if getattr(settings, "RAG_USE_SUMMARIES", False) and len(extracted_text or "") >= getattr(settings, "RAG_SUMMARY_MIN_CHARS", 15000):
        try:
            collection.delete(where={"policy_id": policy_id, "is_summary": True})
        except Exception as e:
            logger.debug("RAG delete existing summary chunks: %s", e)
        try:
            from app.services.rag_summaries import index_summary_chunks
            index_summary_chunks(extracted_text, policy_id, policy_name, collection)
        except Exception as e:
            logger.debug("RAG summary indexing skipped: %s", e)
    return True


def delete_policy_from_index(policy_id: str) -> None:
    """Remove all chunks for the given policy_id from RAG storage (Chroma or MySQL)."""
    backend = (getattr(settings, "RAG_STORAGE_BACKEND", None) or "chroma").strip().lower()
    if backend == "mysql":
        from app.services.rag_storage_mysql import delete_policy_from_index_mysql
        delete_policy_from_index_mysql(policy_id)
        return
    pair = _get_client_and_collection()
    if not pair:
        return
    _client, collection = pair
    try:
        collection.delete(where={"policy_id": policy_id})
        logger.info("RAG deleted chunks for policy_id=%s", policy_id)
    except Exception as e:
        logger.warning("RAG delete failed for policy_id=%s: %s", policy_id, e)


def get_indexed_count() -> int:
    """Return the number of documents in the RAG collection (Chroma or MySQL), or 0 if unavailable."""
    backend = (getattr(settings, "RAG_STORAGE_BACKEND", None) or "chroma").strip().lower()
    if backend == "mysql":
        from app.services.rag_storage_mysql import get_indexed_count_mysql
        return get_indexed_count_mysql()
    pair = _get_client_and_collection()
    if not pair:
        return 0
    _client, collection = pair
    try:
        return collection.count()
    except Exception as e:
        logger.debug("RAG count failed: %s", e)
        return 0


def warmup_rag() -> None:
    """
    Pre-warm RAG: load embedding model and storage so first upload/reindex is fast.
    Safe to call at startup from a background thread.
    """
    backend = (getattr(settings, "RAG_STORAGE_BACKEND", None) or "chroma").strip().lower()
    if backend == "mysql":
        try:
            retrieve("warmup", top_k=1)
            logger.info("RAG (MySQL) warmup completed")
        except Exception as e:
            logger.warning("RAG (MySQL) warmup failed (non-fatal): %s", e)
        return
    if not _is_rag_available():
        return
    try:
        pair = _get_client_and_collection()
        if not pair:
            return
        _client, collection = pair
        collection.query(query_texts=["warmup"], n_results=1)
        logger.info("RAG warmup completed")
    except Exception as e:
        logger.warning("RAG warmup failed (non-fatal): %s", e)


def _embed_query_with_cache(query: str) -> list[float] | None:
    """Return query embedding, using cache if enabled. Returns None if embedding fails."""
    from app.services import rag_cache
    if getattr(settings, "RAG_CACHE_EMBEDDINGS", True):
        cached = rag_cache.get_cached_embedding(query)
        if cached is not None:
            return cached
    try:
        ef = _make_embedding_function()
        embs = ef([query])
        if not embs:
            return None
        emb = embs[0]
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
        else:
            emb = list(emb)
        if getattr(settings, "RAG_CACHE_EMBEDDINGS", True):
            rag_cache.set_cached_embedding(query, emb)
        return emb
    except Exception as e:
        logger.debug("Query embedding failed: %s", e)
        return None


def retrieve(
    query: str,
    top_k: int | None = None,
    policy_id: str | None = None,
    use_summaries_only: bool = False,
) -> list[dict]:
    """
    Embed query, similarity search in RAG storage (Chroma or MySQL), return list of
    { "text", "policy_id", "chunk_index", "policy_name", "score" }.
    """
    backend = (getattr(settings, "RAG_STORAGE_BACKEND", None) or "chroma").strip().lower()
    if backend == "mysql":
        from app.services.rag_storage_mysql import retrieve_mysql
        return retrieve_mysql(query, top_k=top_k, policy_id=policy_id, use_summaries_only=use_summaries_only)
    pair = _get_client_and_collection()
    if not pair:
        return []
    _client, collection = pair
    query = (query or "").strip()
    if not query:
        return []
    k_max = getattr(settings, "RAG_TOP_K_MAX", 10)
    k_requested = top_k if top_k is not None else getattr(settings, "RAG_TOP_K", 5)
    k_query = max(k_max, k_requested)
    where = None
    if policy_id is not None:
        where = {"policy_id": policy_id}
    if use_summaries_only and getattr(settings, "RAG_USE_SUMMARIES", False):
        where = (where or {}) | {"is_summary": True}
    use_embed_cache = getattr(settings, "RAG_CACHE_EMBEDDINGS", True)
    query_embeddings_arg = None
    if use_embed_cache:
        query_emb = _embed_query_with_cache(query)
        if query_emb is not None:
            query_embeddings_arg = [query_emb]
    try:
        if query_embeddings_arg is not None:
            results = collection.query(
                query_embeddings=query_embeddings_arg,
                n_results=k_query,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=k_query,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
    except Exception as e:
        logger.warning("RAG retrieve failed: %s", e)
        return []
    if not results or not results.get("documents") or not results["documents"][0]:
        return []
    docs = results["documents"][0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]
    min_sim = max(0.70, getattr(settings, "RAG_MIN_SIMILARITY", 0.75))
    high_sim_thresh = getattr(settings, "RAG_HIGH_SIMILARITY_THRESHOLD", 0.85)
    k_min = getattr(settings, "RAG_TOP_K_MIN", 3)
    out = []
    for i, doc in enumerate(docs):
        dist = distances[i] if i < len(distances) else 1.0
        score = 1.0 - float(dist)
        if score < min_sim:
            continue
        meta = metadatas[i] if i < len(metadatas) else {}
        out.append({
            "text": doc,
            "policy_id": meta.get("policy_id"),
            "chunk_index": meta.get("chunk_index"),
            "policy_name": meta.get("policy_name"),
            "score": score,
        })
    if getattr(settings, "RAG_USE_RERANKER", False):
        try:
            from app.services.rag_reranker import rerank
            top_n = getattr(settings, "RAG_RERANK_TOP_N", 5)
            out = rerank(query, out, top_n=top_n)
        except Exception as e:
            logger.debug("RAG re-ranker skipped: %s", e)
    if not out:
        return []
    max_score = max(c.get("score", 0) for c in out)
    if max_score >= high_sim_thresh:
        k_final = min(k_min, len(out))
    else:
        k_final = min(k_requested, len(out))
    return out[:k_final]


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken (cl100k_base) or char heuristic. Used for context budget."""
    if not (text or "").strip():
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(0, len(text) // CHARS_PER_TOKEN)


def trim_chunks_to_token_budget(
    chunks: list[dict],
    system_prompt: str,
    content_prefix: str,
    content_suffix: str,
    max_context_tokens: int | None = None,
) -> str:
    """
    Build excerpts string from chunks so that
    count(system_prompt) + count(content_prefix + excerpts + content_suffix) <= max_context_tokens.
    Sorts chunks by similarity score (descending) so highest-relevance chunks are kept;
    drops only lowest-scoring chunks from the end until under budget.
    """
    max_ctx = max_context_tokens if max_context_tokens is not None else getattr(settings, "RAG_ASK_MAX_CONTEXT_TOKENS", 4096)
    if max_ctx <= 0:
        return "\n\n---\n\n".join(c.get("text", "") for c in chunks)
    # Keep highest-scoring chunks first; only trim lowest-scoring
    sorted_chunks = sorted(chunks, key=lambda c: -(c.get("score") if c.get("score") is not None else 0.0))
    budget = max_ctx - count_tokens(system_prompt) - count_tokens(content_prefix) - count_tokens(content_suffix)
    if budget <= 0:
        return ""
    separator = "\n\n---\n\n"
    for take in range(len(sorted_chunks), 0, -1):
        excerpts_text = separator.join(c.get("text", "") for c in sorted_chunks[:take])
        if count_tokens(excerpts_text) <= budget:
            return excerpts_text
    return ""


def sanitize_query(query: str, max_length: int | None = None) -> str:
    """
    Strip control characters and normalize whitespace. Optionally truncate to max_length.
    Used to mitigate prompt injection and abuse.
    """
    if not query:
        return ""
    length = max_length if max_length is not None else getattr(settings, "RAG_ASK_MAX_QUERY_LENGTH", 500)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > length:
        cleaned = cleaned[:length].rstrip()
    return cleaned
