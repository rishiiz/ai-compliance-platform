"""Policy-related API routes."""

import asyncio
import logging
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mongoengine import Q
from app.config import settings
from app.models.app_settings import AppSettings
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.policy import Policy
from app.models.rule import Rule
from app.models.user import User
from app.schemas.rule_data import validate_rule_data
from app.services.zip_policy_service import ALLOWED_EXTENSIONS, extract_text_from_policy_file
from app.services.policy_compare import compare_policies
from app.routes.auth_routes import get_current_user
from app.services.rag_service import (
    get_indexed_count,
    get_rag_status,
    index_policy_chunks,
    retrieve,
    sanitize_query,
    trim_chunks_to_token_budget,
)
from app.services.rule_extractor import RuleExtractionError, extract_rules_from_text, _fallback_rules_from_text
from app.services.company_policy_search import search_company_policy_db

router = APIRouter(prefix="/policy", tags=["policy"])
logger = logging.getLogger(__name__)

# Upload: run RAG index + rule extraction in parallel with this timeout (seconds)
UPLOAD_PROCESS_TIMEOUT = 120

_rag_ask_timestamps: dict[str, list[float]] = {}
RAG_ASK_WINDOW_SEC = 3600


class PolicyAskRequest(BaseModel):
    """Request body for Ask policy (RAG Q&A)."""
    query: str
    policy_id: str | None = None


def _rag_ask_rate_limit_check(user_id: str) -> None:
    """Raise HTTPException 429 if user exceeded RAG Ask rate limit in the last hour."""
    limit = getattr(settings, "RAG_ASK_RATE_LIMIT_PER_HOUR", 60)
    if limit <= 0:
        return
    now_sec = time.time()
    cutoff = now_sec - RAG_ASK_WINDOW_SEC
    if user_id not in _rag_ask_timestamps:
        _rag_ask_timestamps[user_id] = []
    _rag_ask_timestamps[user_id] = [t for t in _rag_ask_timestamps[user_id] if t > cutoff]
    if len(_rag_ask_timestamps[user_id]) >= limit:
        logger.warning("RAG Ask rate limit exceeded | user_id=%s | limit=%s", user_id, limit)
        raise HTTPException(
            status_code=429,
            detail=f"Too many Ask policy requests in the last hour (limit: {limit}). Try again later.",
        )
    _rag_ask_timestamps[user_id].append(now_sec)

# Defaults when AppSettings key is missing (env override optional)
DEFAULT_MAX_FILE_SIZE_MB = int(os.environ.get("POLICY_UPLOAD_MAX_FILE_SIZE_MB", "50"))
DEFAULT_MAX_UPLOADS_PER_HOUR = int(os.environ.get("POLICY_UPLOAD_MAX_PER_HOUR", "30"))

CHUNK_SIZE = 1024 * 1024  # 1 MB for streaming read


def _get_int_setting(key: str, default: int) -> int:
    """Get integer setting from AppSettings by key, or default if missing/invalid."""
    row = AppSettings.objects(key=key).first()
    if not row or not row.value:
        return default
    try:
        return int(row.value.strip())
    except ValueError:
        return default


def _rule_to_response(rule: Rule) -> dict:
    """Serialize a Rule model to a JSON-suitable dict."""
    policy = getattr(rule, 'policy_id', None)
    return {
        "id": str(rule.id),
        "policy_id": str(policy.id) if hasattr(policy, 'id') else str(policy) if policy else None,
        "rule_data": rule.rule_data,
        "severity": rule.severity,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
    }


@router.get("/compare")
def policy_compare_route(
    old_policy_id: str = Query(..., description="Policy ID for old version"),
    new_policy_id: str = Query(..., description="Policy ID for new version"),
    compute_impact: bool = Query(True, description="Compute new violations count if DB connected"),
) -> dict:
    """Compare two policy versions: rule diff (only in old, only in new, in both) and optional impact count."""
    try:
        return compare_policies(old_policy_id, new_policy_id, compute_impact=compute_impact)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# Max chars of policy text to send to LLM when RAG index is empty (fallback answer from raw text)
ASK_FALLBACK_MAX_CHARS = 12_000

SYSTEM_PROMPT_RAG = """You are a policy compliance assistant.

You must answer using ONLY the provided policy excerpts.

Rules:
1. Do NOT use prior knowledge.
2. Do NOT infer missing details.
3. If the excerpts do not explicitly contain the answer,
   respond exactly with:
   "Not found in the provided documents."
4. When the answer contains a specific numeric limit, rule, or restriction,
   return the exact sentence verbatim from the excerpts.
   Do not rephrase it.
5. If an exact sentence cannot be located,
   respond exactly:
   "Exact sentence not found in excerpts."
"""
SYSTEM_PROMPT_FALLBACK = """You are a policy compliance assistant.

You must answer using ONLY the provided policy text.

Rules:
1. Do NOT use prior knowledge.
2. Do NOT infer missing details.
3. If the text does not explicitly contain the answer,
   respond exactly with:
   "Not found in the provided documents."
4. When the answer contains a specific numeric limit, rule, or restriction,
   return the exact sentence verbatim from the text.
5. If an exact sentence cannot be located,
   respond exactly:
   "Exact sentence not found in excerpts."
"""
SYSTEM_PROMPT_COMPANY_DB = """You are a policy compliance assistant.
You must answer using ONLY the provided policy content from the company database.
Do NOT use prior knowledge. If the content does not contain the answer, respond exactly:
"Not found in the provided policy content."
"""


def _do_ask_sync(
    cleaned: str,
    policy_id: str | None,
    fallback_policies: list[dict],
    use_summaries_only: bool = False,
) -> tuple[str, list[dict] | None, float, float, int, int | None]:
    """
    Sync helper: first try company DB (policy content from external DB), then Groq.
    If no company DB content, fall back to Chroma RAG or policy text.
    Returns (answer_text, chunks_used or None, retrieval_time_ms, llm_time_ms, tokens_sent, tokens_returned).
    Run via asyncio.to_thread.
    """
    from app.services.llm_client import get_completion_client, get_completion_model
    from app.services import rag_cache
    from app.services.rag_service import count_tokens

    t0 = time.perf_counter()
    # Flow: user question -> search company DB for policy content -> Groq answers from that -> output
    use_company_db = getattr(settings, "USE_COMPANY_DB_FOR_ASK", True)
    if use_company_db:
        limit = getattr(settings, "COMPANY_POLICY_SEARCH_LIMIT", 10)
        company_results = search_company_policy_db(cleaned, limit=limit)
        context_parts = []
        for r in company_results:
            content = (r.get("content") or "").strip()
            if content:
                title = r.get("title")
                if title:
                    context_parts.append(f"[{title}]\n{content}")
                else:
                    context_parts.append(content)
        context = "\n\n---\n\n".join(context_parts).strip()
        if context:
            retrieval_ms = (time.perf_counter() - t0) * 1000.0
            user_content = f"""Policy content from company database:\n\n{context}\n\nUser question: {cleaned}\n\nAnswer (based only on the policy content above):"""
            tokens_sent = count_tokens(SYSTEM_PROMPT_COMPANY_DB) + count_tokens(user_content)
            try:
                t1 = time.perf_counter()
                client = get_completion_client()
                max_tokens = getattr(settings, "RAG_ASK_MAX_TOKENS", 500)
                temperature = getattr(settings, "RAG_ASK_TEMPERATURE", 0.2)
                response = client.chat.completions.create(
                    model=get_completion_model(),
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_COMPANY_DB},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                llm_ms = (time.perf_counter() - t1) * 1000.0
                answer = (response.choices[0].message.content or "").strip() if response.choices else ""
                usage = getattr(response, "usage", None)
                tokens_returned = int(usage.completion_tokens) if usage and hasattr(usage, "completion_tokens") else None
                if answer:
                    from app.services import rag_metrics
                    rag_metrics.record(retrieval_time_ms=retrieval_ms, llm_time_ms=llm_ms, total_latency_ms=(time.perf_counter() - t0) * 1000.0, tokens_sent=tokens_sent, tokens_returned=tokens_returned)
                    return (answer, None, retrieval_ms, llm_ms, tokens_sent, tokens_returned)
            except Exception as e:
                logger.warning("Ask (company DB) LLM call failed: %s", e)
            # If LLM failed, fall through to Chroma/fallback
        else:
            retrieval_ms = (time.perf_counter() - t0) * 1000.0
            from app.services import rag_metrics
            rag_metrics.record(retrieval_time_ms=retrieval_ms, llm_time_ms=0.0, total_latency_ms=(time.perf_counter() - t0) * 1000.0, tokens_sent=0, tokens_returned=None)
            return (
                "No relevant policy content found in the company database. Ask uses the table 'policy_documents' and column 'content'. Create that table in Dollar (or your company DB), add rows with policy text (e.g. 'Data retention is 7 years'), then try again. See SAMPLE_DATA_FOR_VIOLATIONS.md for SQL.",
                None,
                retrieval_ms,
                0.0,
                0,
                None,
            )

    top_k = getattr(settings, "RAG_TOP_K", 5)
    chunks = rag_cache.get_cached_chunks(cleaned, policy_id)
    if chunks is None:
        chunks = retrieve(cleaned, top_k=top_k, policy_id=policy_id, use_summaries_only=use_summaries_only)
    retrieval_ms = (time.perf_counter() - t0) * 1000.0
    excerpts_text = ""
    if chunks:
        max_ctx = getattr(settings, "RAG_ASK_MAX_CONTEXT_TOKENS", 4096)
        content_prefix = "Policy excerpts:\n\n"
        content_suffix = f"\n\nUser question: {cleaned}\n\nAnswer (based only on the policy excerpts above):"
        excerpts_text = trim_chunks_to_token_budget(
            chunks, SYSTEM_PROMPT_RAG, content_prefix, content_suffix, max_context_tokens=max_ctx
        )
    if not excerpts_text or not excerpts_text.strip():
        fallback_text = ""
        if fallback_policies:
            parts = [f"[Policy: {p['name']}]\n{p['text']}" for p in fallback_policies if p.get("text")]
            fallback_text = "\n\n".join(parts).strip()
        if fallback_text:
            max_chars = getattr(settings, "RAG_ASK_FALLBACK_MAX_CHARS", ASK_FALLBACK_MAX_CHARS)
            if len(fallback_text) > max_chars:
                fallback_text = fallback_text[: max_chars - 50] + "\n\n[... truncated ...]"
            user_content = f"""Policy text:\n\n{fallback_text}\n\nUser question: {cleaned}\n\nAnswer (based only on the policy text above):"""
            try:
                t1 = time.perf_counter()
                client = get_completion_client()
                max_tokens = getattr(settings, "RAG_ASK_MAX_TOKENS", 500)
                temperature = getattr(settings, "RAG_ASK_TEMPERATURE", 0.2)
                response = client.chat.completions.create(
                    model=get_completion_model(),
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_FALLBACK},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                llm_ms = (time.perf_counter() - t1) * 1000.0
                answer = (response.choices[0].message.content or "").strip() if response.choices else ""
                tokens_sent = count_tokens(SYSTEM_PROMPT_FALLBACK) + count_tokens(user_content)
                usage = getattr(response, "usage", None)
                tokens_returned = int(usage.completion_tokens) if usage and hasattr(usage, "completion_tokens") else None
                if answer:
                    total_ms = (time.perf_counter() - t0) * 1000.0
                    from app.services import rag_metrics
                    rag_metrics.record(retrieval_time_ms=retrieval_ms, llm_time_ms=llm_ms, total_latency_ms=total_ms, tokens_sent=tokens_sent, tokens_returned=tokens_returned)
                    return (answer + "\n\n(Answer from policy text; RAG index is still building. For best results, use 'Index existing policies' when ready.)", None, retrieval_ms, llm_ms, tokens_sent, tokens_returned)
            except Exception as e:
                logger.warning("Ask fallback (policy text) LLM call failed: %s", e)
        total_ms = (time.perf_counter() - t0) * 1000.0
        from app.services import rag_metrics
        rag_metrics.record(retrieval_time_ms=retrieval_ms, llm_time_ms=0.0, total_latency_ms=total_ms, tokens_sent=0, tokens_returned=None)
        indexed_count = get_indexed_count()
        if policy_id is not None:
            answer_msg = (
                "No indexed content for the selected policy. "
                "Try 'All policies' to search across all indexed policies, or run 'Index existing policies' again. "
                "If this policy was uploaded before RAG was enabled, re-upload its PDF so it can be indexed."
            )
        elif indexed_count > 0:
            answer_msg = (
                "Search returned no results even though the index has content. "
                "Check that GROQ_API_KEY is set in backend .env and see server logs for 'RAG retrieve failed'."
            )
        else:
            answer_msg = (
                "No policy documents are indexed yet. Upload policy PDFs first (Upload Policy), then try again. "
                "If you already uploaded policies, use 'Index existing policies' above to index them for Q&A."
            )
        return (answer_msg, None, retrieval_ms, 0.0, 0, None)
    user_content = f"""Policy excerpts:\n\n{excerpts_text}\n\nUser question: {cleaned}\n\nAnswer (based only on the policy excerpts above):"""
    tokens_sent = count_tokens(SYSTEM_PROMPT_RAG) + count_tokens(user_content)
    try:
        t1 = time.perf_counter()
        client = get_completion_client()
        max_tokens = getattr(settings, "RAG_ASK_MAX_TOKENS", 500)
        temperature = getattr(settings, "RAG_ASK_TEMPERATURE", 0.2)
        response = client.chat.completions.create(
            model=get_completion_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RAG},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        llm_ms = (time.perf_counter() - t1) * 1000.0
        answer = (response.choices[0].message.content or "").strip() if response.choices else ""
        usage = getattr(response, "usage", None)
        tokens_returned = int(usage.completion_tokens) if usage and hasattr(usage, "completion_tokens") else None
    except Exception as e:
        logger.warning("RAG Ask LLM call failed: %s", e)
        raise HTTPException(status_code=502, detail="Failed to generate answer.") from e
    total_ms = (time.perf_counter() - t0) * 1000.0
    from app.services import rag_metrics
    rag_metrics.record(retrieval_time_ms=retrieval_ms, llm_time_ms=llm_ms, total_latency_ms=total_ms, tokens_sent=tokens_sent, tokens_returned=tokens_returned)
    return (answer or "No answer could be generated.", chunks, retrieval_ms, llm_ms, tokens_sent, tokens_returned)


def _stream_ask_sync_producer(
    cleaned: str,
    policy_id: str | None,
    fallback_policies: list[dict],
    out_queue: queue.Queue[str | None],
    use_summaries_only: bool = False,
) -> None:
    """Run in thread: stream LLM deltas into queue. Puts None when done. Company DB first, then Chroma."""
    from app.services.llm_client import get_completion_client, get_completion_model
    from app.services import rag_cache
    import json

    try:
        use_company_db = getattr(settings, "USE_COMPANY_DB_FOR_ASK", True)
        if use_company_db:
            limit = getattr(settings, "COMPANY_POLICY_SEARCH_LIMIT", 10)
            company_results = search_company_policy_db(cleaned, limit=limit)
            context_parts = []
            for r in company_results:
                content = (r.get("content") or "").strip()
                if content:
                    title = r.get("title")
                    if title:
                        context_parts.append(f"[{title}]\n{content}")
                    else:
                        context_parts.append(content)
            context = "\n\n---\n\n".join(context_parts).strip()
            if context:
                user_content = f"""Policy content from company database:\n\n{context}\n\nUser question: {cleaned}\n\nAnswer (based only on the policy content above):"""
                max_tokens = getattr(settings, "RAG_ASK_MAX_TOKENS", 500)
                temperature = getattr(settings, "RAG_ASK_TEMPERATURE", 0.2)
                client = get_completion_client()
                response = client.chat.completions.create(
                    model=get_completion_model(),
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_COMPANY_DB},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        out_queue.put(f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n")
                out_queue.put("data: [DONE]\n\n")
                out_queue.put(None)
                return
            else:
                msg = "No relevant policy content found in the company database. Ask uses the table 'policy_documents' and column 'content'. Create that table in Dollar (or your company DB), add rows with policy text (e.g. 'Data retention is 7 years'), then try again. See SAMPLE_DATA_FOR_VIOLATIONS.md for SQL."
                out_queue.put(f"data: {json.dumps({'content': msg})}\n\n")
                out_queue.put("data: [DONE]\n\n")
                out_queue.put(None)
                return

        top_k = getattr(settings, "RAG_TOP_K", 5)
        chunks = rag_cache.get_cached_chunks(cleaned, policy_id)
        if chunks is None:
            chunks = retrieve(cleaned, top_k=top_k, policy_id=policy_id, use_summaries_only=use_summaries_only)
        excerpts_text = ""
        if chunks:
            max_ctx = getattr(settings, "RAG_ASK_MAX_CONTEXT_TOKENS", 4096)
            content_prefix = "Policy excerpts:\n\n"
            content_suffix = f"\n\nUser question: {cleaned}\n\nAnswer (based only on the policy excerpts above):"
            excerpts_text = trim_chunks_to_token_budget(
                chunks, SYSTEM_PROMPT_RAG, content_prefix, content_suffix, max_context_tokens=max_ctx
            )
        if not excerpts_text or not excerpts_text.strip():
            answer, _ = _do_ask_sync(cleaned, policy_id, fallback_policies)
            out_queue.put(f"data: {json.dumps({'content': answer})}\n\n")
            out_queue.put("data: [DONE]\n\n")
            out_queue.put(None)
            return
        user_content = f"""Policy excerpts:\n\n{excerpts_text}\n\nUser question: {cleaned}\n\nAnswer (based only on the policy excerpts above):"""
        max_tokens = getattr(settings, "RAG_ASK_MAX_TOKENS", 500)
        temperature = getattr(settings, "RAG_ASK_TEMPERATURE", 0.2)
        client = get_completion_client()
        response = client.chat.completions.create(
            model=get_completion_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RAG},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                out_queue.put(f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n")
        out_queue.put("data: [DONE]\n\n")
    except Exception as e:
        logger.warning("RAG Ask stream failed: %s", e)
        out_queue.put(f"data: {json.dumps({'error': str(e)})}\n\n")
    finally:
        out_queue.put(None)


@router.post("/ask", response_model=None)
async def policy_ask(
    body: PolicyAskRequest,
    current_user: User = Depends(get_current_user),
    stream: bool = Query(False, description="Stream response as SSE"),
) -> dict | StreamingResponse:
    """
    Ask a natural-language question about compliance policy.
    Flow: user question -> search company DB for policy content -> Groq answers from that -> output.
    When USE_COMPANY_DB_FOR_ASK is True (default), policy content is read from the company (external)
    database table (COMPANY_POLICY_TABLE / COMPANY_POLICY_CONTENT_COLUMN). If no company DB or no results,
    falls back to Chroma RAG or policy extracted_text. Response and chunks are cached. Set stream=true for SSE.
    """
    max_len = getattr(settings, "RAG_ASK_MAX_QUERY_LENGTH", 500)
    cleaned = sanitize_query(body.query or "", max_length=max_len)
    if not cleaned:
        raise HTTPException(
            status_code=400,
            detail="Query is required and must be non-empty after sanitization.",
        )
    _rag_ask_rate_limit_check(str(current_user.id))

    from app.services import rag_cache

    if not stream:
        cached = rag_cache.get_cached_response(cleaned, body.policy_id)
        if cached is not None:
            return {"answer": cached}

    policies_with_text_qs = Policy.objects(Q(extracted_text__ne=None) & Q(extracted_text__ne=""))
    if body.policy_id is not None:
        policies_with_text_qs = policies_with_text_qs.filter(id=body.policy_id)
    policies_with_text = list(policies_with_text_qs)
    fallback_policies = [{"name": p.name, "text": (p.extracted_text or "").strip()} for p in policies_with_text if (p.extracted_text or "").strip()]
    use_summaries_only = getattr(settings, "RAG_USE_SUMMARIES", False) and len(cleaned.split()) <= 6

    if stream:
        out_queue: queue.Queue[str | None] = queue.Queue()
        thread = threading.Thread(
            target=_stream_ask_sync_producer,
            args=(cleaned, body.policy_id, fallback_policies, out_queue, use_summaries_only),
        )
        thread.start()

        async def stream_events():
            while True:
                item = await asyncio.to_thread(out_queue.get)
                if item is None:
                    break
                yield item

        return StreamingResponse(
            stream_events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    answer, chunks_used, _r_ms, _l_ms, _t_sent, _t_ret = await asyncio.to_thread(_do_ask_sync, cleaned, body.policy_id, fallback_policies, use_summaries_only)

    if getattr(settings, "RAG_CACHE_RESPONSE", True):
        rag_cache.set_cached_response(cleaned, body.policy_id, answer)
    if chunks_used is not None and getattr(settings, "RAG_CACHE_CHUNKS", True):
        rag_cache.set_cached_chunks(cleaned, body.policy_id, chunks_used)

    return {"answer": answer}


@router.post("/reindex")
def policy_reindex(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Index all policies that have extracted_text into the RAG vector store.
    Use this to backfill the index for policies uploaded before RAG or when indexing failed at upload.
    """
    logger.info("RAG reindex requested")
    policies_with_text = list(Policy.objects(Q(extracted_text__ne=None) & Q(extracted_text__ne="")))
    indexed = 0
    for i, p in enumerate(policies_with_text):
        ok = index_policy_chunks(p.extracted_text, str(p.id), p.name)
        if ok:
            indexed += 1
        logger.info("RAG policy %s/%s: policy_id=%s name=%s ok=%s", i + 1, len(policies_with_text), p.id, p.name, ok)
    logger.info("RAG reindex completed | indexed=%s | total_with_text=%s", indexed, len(policies_with_text))
    out = {"indexed": indexed, "total_with_text": len(policies_with_text)}
    if indexed == 0 and len(policies_with_text) > 0:
        status = get_rag_status()
        out["rag_available"] = status.get("available", False)
        out["hint"] = status.get("reason", "RAG is not available. Use local embeddings (pip install -r requirements.txt) and restart the backend.")
    logger.info("RAG reindex response: indexed=%s total=%s", out["indexed"], out["total_with_text"])
    return out


@router.get("/rag-status")
def policy_rag_status(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Return RAG index status: indexed_count and total policies with text.
    Used by Ask policy page to show status and optionally auto-trigger reindex.
    """
    total_with_text = Policy.objects(Q(extracted_text__ne=None) & Q(extracted_text__ne="")).count()
    indexed_count = get_indexed_count()
    status = get_rag_status()
    return {
        "indexed_count": indexed_count,
        "total_with_text": total_with_text,
        "rag_available": status.get("available", False),
        "hint": status.get("reason", ""),
    }


@router.get("")
def list_policies() -> list:
    """List all policies with rules count."""
    policies = Policy.objects().order_by("-uploaded_at")
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "version": p.version,
            "is_active": p.is_active,
            "uploaded_at": p.uploaded_at.isoformat() if hasattr(p, 'uploaded_at') and p.uploaded_at else None,
            "rules_count": Rule.objects(policy_id=p.id).count(),
        }
        for p in policies
    ]


@router.post("/upload")
async def upload_policy(
    file: UploadFile = File(...),
) -> list[dict]:
    """
    Upload a policy file (PDF, CSV, or TXT), extract text, extract rules, store policy
    and rules in the database, and return the stored rules.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning("Policy upload rejected: unsupported file type %s", ext)
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF, CSV, or TXT document",
        )

    # Rate limit: max successful uploads per hour (global)
    max_per_hour = _get_int_setting("policy_upload_max_per_hour", DEFAULT_MAX_UPLOADS_PER_HOUR)
    if max_per_hour > 0:
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        count = AuditLog.objects(
            action_type="policy_uploaded",
            timestamp__gte=since,
        ).count()
        if count >= max_per_hour:
            logger.warning("Policy upload rate limit exceeded | count=%s | limit=%s", count, max_per_hour)
            raise HTTPException(
                status_code=429,
                detail=f"Too many policy uploads in the last hour (limit: {max_per_hour}). Try again later.",
            )

    # Per-file size limit (configurable MB)
    max_mb = _get_int_setting("policy_upload_max_file_size_mb", DEFAULT_MAX_FILE_SIZE_MB)
    max_bytes = max_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            logger.warning("Policy upload rejected: file too large | size=%s | limit_mb=%s", total, max_mb)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_mb} MB.",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    text = extract_text_from_policy_file(content, file.filename or "")
    if not (text or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the file. Ensure it is a valid PDF, CSV, or TXT with readable content.",
        )

    policy_name = Path(file.filename or "policy.pdf").stem
    # Same name: increment version and mark previous versions inactive
    existing = Policy.objects(name=policy_name)
    if existing:
        max_version = max([p.version for p in existing]) if existing else 0
        new_version = max_version + 1
        for p in existing:
            p.is_active = False
            p.save()
        policy = Policy(name=policy_name, version=new_version, is_active=True)
    else:
        policy = Policy(name=policy_name, version=1, is_active=True)
    policy.extracted_text = text
    policy.save()

    # Wait only for rule extraction so upload returns quickly; RAG indexing runs in background
    rule_dicts: list[dict] = []
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_rules = executor.submit(extract_rules_from_text, text, str(policy.id))
        try:
            rule_dicts = future_rules.result(timeout=UPLOAD_PROCESS_TIMEOUT)
        except FuturesTimeoutError:
            logger.warning("Policy upload: rule extraction timed out after %ss; using fallback rules", UPLOAD_PROCESS_TIMEOUT)
            rule_dicts = _fallback_rules_from_text(text)
        except RuleExtractionError as e:
            logger.warning("Policy upload: rule extraction failed | error=%s", str(e))
            raise HTTPException(status_code=422, detail=str(e)) from e

    validated_rules = []
    for i, rd in enumerate(rule_dicts):
        try:
            validated = validate_rule_data(rd)
            validated_rules.append(validated)
        except ValueError as e:
            logger.warning(
                "Policy upload: rule validation failed | index=%s | error=%s",
                i,
                str(e),
            )
            raise HTTPException(
                status_code=422,
                detail=f"Rule at index {i} failed validation: {e}",
            ) from e

    stored_rules = []
    for rd in validated_rules:
        severity = rd.get("severity") or "medium"
        rule = Rule(
            policy_id=policy,
            rule_data=rd,
            severity=severity,
        )
        rule.save()
        stored_rules.append(rule)

    # Index policy in RAG in background so upload response returns quickly (rules already loaded)
    def _index_in_background() -> None:
        try:
            index_policy_chunks(text, str(policy.id), policy_name)
        except Exception as e:
            logger.warning("RAG background index failed for policy_id=%s: %s", policy.id, e)
    threading.Thread(target=_index_in_background, daemon=True).start()

    AuditLog(
        action_type="policy_uploaded",
        entity_type="policy",
        entity_id=str(policy.id),
        performed_by="system",
        meta_data={
            "policy_name": policy_name,
            "filename": file.filename,
            "rules_count": len(stored_rules),
        },
    ).save()
    Notification(
        type="success",
        title="Policy uploaded",
        body=f'"{policy_name}" uploaded with {len(stored_rules)} rules extracted.',
        read=False,
    ).save()
    
    logger.info(
        "Policy upload completed | policy_name=%s | policy_id=%s | version=%s | rules_count=%s",
        policy_name,
        policy.id,
        policy.version,
        len(stored_rules),
    )
    return [_rule_to_response(rule) for rule in stored_rules]


# ─────────────────────────────────────────────────────────────────────────────────
# ZIP Upload: extract → Supabase Storage → AI validation → DB (if compliant)
# ─────────────────────────────────────────────────────────────────────────────────

class ZipUploadResult(BaseModel):
    """Per-file result in a ZIP upload response."""
    filename: str
    file_type: str
    storage_url: str
    is_compliant: bool
    compliance_score: float
    summary: str
    issues: list[str] = []
    suggestions: list[str] = []
    policy_id: str | None = None
    rules_count: int | None = None
    error: str = ""


@router.post("/upload-zip")
async def upload_policy_zip(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Upload a ZIP archive containing policy files (PDF, CSV, TXT).

    For each file inside the ZIP:
    1. Text is extracted (PDF→PyMuPDF, CSV→rows, TXT→plain).
    2. The raw file is uploaded to Supabase Storage.
    3. An AI compliance agent validates the policy text.
    4. If compliant → Policy + Rules are created in the database, RAG-indexed.
    5. If not compliant → AI suggestions are returned (not pushed to DB).

    Returns a summary of all files processed with their compliance status.
    """
    from app.services.zip_policy_service import extract_and_upload_zip
    from app.services.policy_validator import validate_policy_compliance

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive.")

    # Size limit for the whole ZIP
    max_mb = getattr(settings, "ZIP_UPLOAD_MAX_FILE_SIZE_MB", 50)
    max_bytes = max_mb * 1024 * 1024
    chunks_data: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"ZIP file too large. Maximum size is {max_mb} MB.",
            )
        chunks_data.append(chunk)

    zip_bytes = b"".join(chunks_data)

    # Extract and upload all files to Supabase Storage
    try:
        extracted_files = await asyncio.to_thread(
            extract_and_upload_zip, zip_bytes, file.filename
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("ZIP extraction error: %s", e)
        raise HTTPException(status_code=422, detail=f"Failed to extract ZIP: {e}") from e

    if not extracted_files:
        raise HTTPException(
            status_code=422,
            detail="No supported files (PDF, CSV, TXT) found inside the ZIP.",
        )

    results: list[dict] = []

    for ef in extracted_files:
        result: dict = {
            "filename": ef.filename,
            "file_type": ef.file_type,
            "storage_url": ef.storage_url,
            "is_compliant": False,
            "compliance_score": 0.0,
            "summary": "",
            "issues": [],
            "suggestions": [],
            "policy_id": None,
            "rules_count": None,
            "error": "",
        }

        # Run AI compliance validation
        try:
            validation = await asyncio.to_thread(
                validate_policy_compliance, ef.text_content, ef.filename
            )
        except Exception as e:
            logger.error("Validation error for %s: %s", ef.filename, e)
            result["error"] = f"Validation failed: {e}"
            AuditLog(
                action_type="policy_zip_validation_error",
                entity_type="policy",
                entity_id="0",
                performed_by=current_user.email,
                meta_data={"zip_filename": file.filename, "file": ef.filename, "error": str(e)},
            ).save()
            results.append(result)
            continue

        result["is_compliant"] = validation.is_compliant
        result["compliance_score"] = validation.compliance_score
        result["summary"] = validation.summary
        result["issues"] = validation.issues
        result["suggestions"] = validation.suggestions
        result["error"] = validation.error

        if not validation.is_compliant:
            # Log the rejection with AI suggestions
            logger.info("Policy non-compliant: file=%s score=%.2f", ef.filename, validation.compliance_score)
            AuditLog(
                action_type="policy_zip_validation_failed",
                entity_type="policy",
                entity_id="0",
                performed_by=current_user.email,
                meta_data={
                    "zip_filename": file.filename,
                    "file": ef.filename,
                    "compliance_score": validation.compliance_score,
                    "issues": validation.issues,
                },
            ).save()
            Notification(
                type="warning",
                title="Policy not compliant",
                body=f'"{ef.filename}" from "{file.filename}" did not pass compliance check (score: {validation.compliance_score:.0%}). Review AI suggestions.',
                read=False,
            ).save()
            results.append(result)
            continue

        # ── Compliant: push to DB ────────────────────────────────────────────────
        policy_name = Path(ef.filename).stem
        existing = Policy.objects(name=policy_name)
        if existing:
            max_version = max([p.version for p in existing]) if existing else 0
            for p in existing:
                p.is_active = False
                p.save()
            policy_obj = Policy(
                name=policy_name,
                version=max_version + 1,
                is_active=True,
                source_zip=file.filename,
                storage_path=ef.storage_path,
            )
        else:
            policy_obj = Policy(
                name=policy_name,
                version=1,
                is_active=True,
                source_zip=file.filename,
                storage_path=ef.storage_path,
            )
        policy_obj.extracted_text = ef.text_content
        policy_obj.save()

        # Extract rules with timeout fallback
        rule_dicts: list[dict] = []
        with ThreadPoolExecutor(max_workers=1) as executor:
            future_rules = executor.submit(extract_rules_from_text, ef.text_content, str(policy_obj.id))
            try:
                rule_dicts = future_rules.result(timeout=UPLOAD_PROCESS_TIMEOUT)
            except FuturesTimeoutError:
                logger.warning("ZIP upload: rule extraction timed out for %s; using fallback", ef.filename)
                rule_dicts = _fallback_rules_from_text(ef.text_content)
            except RuleExtractionError as e:
                logger.warning("ZIP upload: rule extraction failed for %s: %s", ef.filename, e)
                rule_dicts = _fallback_rules_from_text(ef.text_content)

        stored_rules = []
        for rd in rule_dicts:
            try:
                validated = validate_rule_data(rd)
            except ValueError:
                continue
            rule = Rule(
                policy_id=policy_obj,
                rule_data=validated,
                severity=rd.get("severity") or "medium",
            )
            rule.save()
            stored_rules.append(rule)

        # Background RAG indexing
        _policy_id_ref = str(policy_obj.id)
        _policy_name_ref = policy_name
        _text_ref = ef.text_content

        def _index_bg() -> None:
            try:
                index_policy_chunks(_text_ref, _policy_id_ref, _policy_name_ref)
            except Exception as exc:
                logger.warning("RAG background index failed for %s: %s", _policy_name_ref, exc)

        threading.Thread(target=_index_bg, daemon=True).start()

        AuditLog(
            action_type="policy_zip_uploaded",
            entity_type="policy",
            entity_id=str(policy_obj.id),
            performed_by=current_user.email,
            meta_data={
                "zip_filename": file.filename,
                "policy_name": policy_name,
                "file": ef.filename,
                "rules_count": len(stored_rules),
                "compliance_score": validation.compliance_score,
                "storage_path": ef.storage_path,
            },
        ).save()
        Notification(
            type="success",
            title="Policy approved & added",
            body=f'"{policy_name}" from "{file.filename}" passed compliance ({validation.compliance_score:.0%}) and was added with {len(stored_rules)} rules.',
            read=False,
        ).save()

        result["policy_id"] = str(policy_obj.id)
        result["rules_count"] = len(stored_rules)
        logger.info(
            "ZIP policy accepted: file=%s policy_id=%s score=%.2f rules=%s",
            ef.filename, policy_obj.id, validation.compliance_score, len(stored_rules),
        )
        results.append(result)

    compliant_count = sum(1 for r in results if r["is_compliant"])
    return {
        "zip_filename": file.filename,
        "files_processed": len(results),
        "compliant_count": compliant_count,
        "non_compliant_count": len(results) - compliant_count,
        "results": results,
    }
