"""
RAG caching: query→response, query→chunks, and embedding cache.
Uses Redis when REDIS_URL is set, else in-memory TTL caches.
"""

import hashlib
import json
import logging
import threading
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Any = None


def _cache_key(prefix: str, *parts: Any) -> str:
    raw = prefix + "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _use_redis() -> bool:
    url = (getattr(settings, "REDIS_URL", None) or "").strip()
    return bool(url)


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not _use_redis():
        return None
    try:
        import redis
        url = (getattr(settings, "REDIS_URL", None) or "").strip()
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.warning("Redis connect failed, using in-memory cache: %s", e)
        return None


class _InMemoryTTLCache:
    """Simple TTL cache with max size (FIFO eviction when full)."""

    def __init__(self, maxsize: int, ttl_seconds: int):
        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[Any, float]] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._data:
                return None
            val, expiry = self._data[key]
            if time.time() > expiry:
                del self._data[key]
                self._order = [k for k in self._order if k != key]
                return None
            return val

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            now = time.time()
            if key in self._data:
                self._order = [k for k in self._order if k != key]
            elif len(self._data) >= self._maxsize and self._order:
                evict = self._order.pop(0)
                del self._data[evict]
            self._data[key] = (value, now + self._ttl)
            self._order.append(key)


# In-memory caches (used when Redis not configured)
_response_cache: _InMemoryTTLCache | None = None
_chunks_cache: _InMemoryTTLCache | None = None
_embedding_cache: _InMemoryTTLCache | None = None
_cache_lock = threading.Lock()


def _get_response_cache() -> _InMemoryTTLCache:
    global _response_cache
    with _cache_lock:
        if _response_cache is None:
            ttl = getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600)
            maxsize = getattr(settings, "RAG_CACHE_MAX_RESPONSES", 500)
            _response_cache = _InMemoryTTLCache(maxsize, ttl)
        return _response_cache


def _get_chunks_cache() -> _InMemoryTTLCache:
    global _chunks_cache
    with _cache_lock:
        if _chunks_cache is None:
            ttl = getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600)
            maxsize = getattr(settings, "RAG_CACHE_MAX_CHUNKS", 200)
            _chunks_cache = _InMemoryTTLCache(maxsize, ttl)
        return _chunks_cache


def _get_embedding_cache() -> _InMemoryTTLCache:
    global _embedding_cache
    with _cache_lock:
        if _embedding_cache is None:
            ttl = getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600)
            maxsize = getattr(settings, "RAG_CACHE_MAX_EMBEDDINGS", 1000)
            _embedding_cache = _InMemoryTTLCache(maxsize, ttl)
        return _embedding_cache


def get_cached_response(normalized_query: str, policy_id: int | None) -> str | None:
    """Return cached answer if present and cache enabled."""
    if not getattr(settings, "RAG_CACHE_RESPONSE", True):
        return None
    key = _cache_key("resp", normalized_query, policy_id if policy_id is not None else "")
    r = _get_redis()
    if r:
        try:
            return r.get(key)
        except Exception as e:
            logger.debug("Redis response cache get failed: %s", e)
            return None
    return _get_response_cache().get(key)


def set_cached_response(normalized_query: str, policy_id: int | None, answer: str) -> None:
    if not getattr(settings, "RAG_CACHE_RESPONSE", True):
        return
    key = _cache_key("resp", normalized_query, policy_id if policy_id is not None else "")
    ttl = getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600)
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, answer)
        except Exception as e:
            logger.debug("Redis response cache set failed: %s", e)
        return
    _get_response_cache().set(key, answer)


def get_cached_chunks(normalized_query: str, policy_id: int | None) -> list[dict] | None:
    """Return cached chunks (list of dicts) if present and cache enabled."""
    if not getattr(settings, "RAG_CACHE_CHUNKS", True):
        return None
    key = _cache_key("chunks", normalized_query, policy_id if policy_id is not None else "")
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("Redis chunks cache get failed: %s", e)
            return None
    val = _get_chunks_cache().get(key)
    return val


def set_cached_chunks(normalized_query: str, policy_id: int | None, chunks: list[dict]) -> None:
    if not getattr(settings, "RAG_CACHE_CHUNKS", True):
        return
    key = _cache_key("chunks", normalized_query, policy_id if policy_id is not None else "")
    ttl = getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600)
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(chunks, default=str))
        except Exception as e:
            logger.debug("Redis chunks cache set failed: %s", e)
        return
    _get_chunks_cache().set(key, chunks)


def get_cached_embedding(text: str) -> list[float] | None:
    """Return cached embedding vector if present and cache enabled."""
    if not getattr(settings, "RAG_CACHE_EMBEDDINGS", True):
        return None
    key = _cache_key("emb", text)
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("Redis embedding cache get failed: %s", e)
            return None
    val = _get_embedding_cache().get(key)
    return val


def set_cached_embedding(text: str, embedding: list[float]) -> None:
    if not getattr(settings, "RAG_CACHE_EMBEDDINGS", True):
        return
    key = _cache_key("emb", text)
    ttl = getattr(settings, "RAG_CACHE_TTL_SECONDS", 3600)
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(embedding))
        except Exception as e:
            logger.debug("Redis embedding cache set failed: %s", e)
        return
    _get_embedding_cache().set(key, embedding)
