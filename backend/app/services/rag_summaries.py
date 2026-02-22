"""
Optional pre-generated section summaries for large policies.
When RAG_USE_SUMMARIES=true and policy text length >= RAG_SUMMARY_MIN_CHARS,
generate section-level summaries and store in Chroma with is_summary=true.
Broad queries can then retrieve from summaries first to reduce tokens.
"""

import logging
import re
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def _split_into_sections(text: str, max_sections: int = 20) -> list[str]:
    """Split text into sections by headings (e.g. '1. ', '## ', numbered) or by double newlines."""
    text = (text or "").strip()
    if not text:
        return []
    # Try heading-style split: "1. Title", "2. Title", "## Title"
    parts = re.split(r"\n(?=\d+\.\s|\d+\)\s|#{1,3}\s)", text, flags=re.MULTILINE)
    if len(parts) <= 1:
        parts = re.split(r"\n\s*\n", text)
    sections = [p.strip() for p in parts if p.strip()][:max_sections]
    return sections


def generate_section_summaries(
    extracted_text: str,
    policy_id: int,
    policy_name: str,
) -> list[dict]:
    """
    Generate short summaries per section. Returns list of { "text", "section_index" }.
    Uses LLM when available; otherwise first ~300 chars per section.
    """
    if not getattr(settings, "RAG_USE_SUMMARIES", False):
        return []
    min_chars = getattr(settings, "RAG_SUMMARY_MIN_CHARS", 15000)
    if len(extracted_text or "") < min_chars:
        return []
    sections = _split_into_sections(extracted_text or "")
    if not sections:
        return []
    out = []
    try:
        from app.services.llm_client import get_completion_client, get_completion_model
        client = get_completion_client()
        model = get_completion_model()
        for i, section in enumerate(sections):
            if len(section) < 100:
                out.append({"text": section, "section_index": i})
                continue
            prompt = f"Summarize this policy section in 1-3 short sentences. Preserve key requirements and numbers.\n\nSection:\n{section[:3000]}"
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=150,
                )
                summary = (response.choices[0].message.content or "").strip() if response.choices else ""
                if summary:
                    out.append({"text": summary, "section_index": i})
                else:
                    out.append({"text": section[:400].rstrip() + ("..." if len(section) > 400 else ""), "section_index": i})
            except Exception as e:
                logger.debug("Section summary LLM failed: %s", e)
                out.append({"text": section[:400].rstrip() + ("..." if len(section) > 400 else ""), "section_index": i})
    except Exception as e:
        logger.warning("RAG section summaries unavailable: %s", e)
        for i, section in enumerate(sections):
            out.append({"text": section[:400].rstrip() + ("..." if len(section) > 400 else ""), "section_index": i})
    return out


def index_summary_chunks(
    extracted_text: str,
    policy_id: int,
    policy_name: str,
    collection: Any,
) -> int:
    """
    Generate section summaries and add them to Chroma as documents with is_summary=true.
    Returns number of summary chunks added. Caller must pass collection (uses its embedding function).
    """
    summaries = generate_section_summaries(extracted_text, policy_id, policy_name)
    if not summaries:
        return 0
    ids = [f"policy_{policy_id}_summary_{s['section_index']}" for s in summaries]
    documents = [s["text"] for s in summaries]
    metadatas = [
        {
            "policy_id": policy_id,
            "policy_name": (policy_name or "")[:500],
            "is_summary": True,
            "section_index": s["section_index"],
        }
        for s in summaries
    ]
    try:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info("RAG indexed %s summary chunks for policy_id=%s", len(documents), policy_id)
        return len(documents)
    except Exception as e:
        logger.warning("RAG index summary chunks failed: %s", e)
        return 0
