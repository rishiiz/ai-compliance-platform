"""Rule extraction from policy text using Groq (Llama). Falls back to placeholder rules when GROQ_API_KEY is missing/invalid."""

import json
import logging
import re

from app.config import settings
from app.services.llm_client import get_completion_client, get_completion_model, is_completion_available

logger = logging.getLogger(__name__)

# Max policy text length sent to LLM (Groq/Llama context limit). Truncate to avoid "reduce the length of the messages" error.
MAX_POLICY_CHARS_FOR_EXTRACTION = 28_000

# Expected keys; condition can be string or structured object
RULE_KEYS = {
    "entity",
    "field",
    "condition",
    "operator",
    "value",
    "severity",
    "policy_clause_text",
}


def _fallback_rules_from_text(text: str) -> list[dict]:
    """Return a small set of valid placeholder rules when Groq LLM is unavailable."""
    # Use first ~200 chars of policy text for clause, or generic message
    clause = (text or "").strip()
    if len(clause) > 200:
        clause = clause[:197] + "..."
    if not clause:
        clause = "Policy clause (set GROQ_API_KEY in .env for AI extraction with Llama)."
    return [
        {
            "entity": "policy_docs",
            "field": "compliance_verified",
            "condition": {"type": "boolean"},
            "operator": "=",
            "value": True,
            "severity": "high",
            "policy_clause_text": "All personal data must be encrypted at rest using AES-256.",
        },
        {
            "entity": "policy_docs",
            "field": "retention_period_years",
            "condition": {"type": "comparison"},
            "operator": "<=",
            "value": 7,
            "severity": "medium",
            "policy_clause_text": "Data retention periods must not exceed 7 years.",
        },
        {
            "entity": "policy_docs",
            "field": "dpa_signed",
            "condition": {"type": "boolean"},
            "operator": "=",
            "value": True,
            "severity": "high",
            "policy_clause_text": "Third-party processors must sign DPAs before data transfer.",
        },
    ]


class RuleExtractionError(Exception):
    """Raised when rule extraction or JSON parsing fails."""

    pass


def _parse_json_safely(raw: str) -> list[dict]:
    """Extract JSON from model output and parse. Handles markdown code blocks."""
    text = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuleExtractionError(f"Invalid JSON from model: {e}") from e
    if not isinstance(parsed, list):
        raise RuleExtractionError("Model output is not a JSON array")
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise RuleExtractionError(f"Item at index {i} is not an object")
        # Preserve structure; ensure expected keys exist
        normalized = {}
        for k in RULE_KEYS:
            if k == "policy_clause_text":
                normalized[k] = item.get(k)
            elif k == "condition":
                normalized[k] = item.get(k, {"type": "equality"})
            else:
                normalized[k] = item.get(k, "" if k != "value" else None)
        if normalized.get("value") is None and "value" in item:
            normalized["value"] = item["value"]
        parsed[i] = normalized
    return parsed


def extract_rules_from_text(text: str, policy_id: int | None = None) -> list[dict]:
    """
    Extract compliance rules from policy text using Groq (Llama 3.3 70B).
    If GROQ_API_KEY is not set/valid, returns fallback placeholder rules so upload still succeeds.
    When RAG is enabled, policy_id is set, and text exceeds RAG_LONG_POLICY_CHARS, uses retrieved
    policy chunks instead of full text to stay within context limits.
    """
    if not text or not text.strip():
        return []

    if not is_completion_available():
        return _fallback_rules_from_text(text)

    long_threshold = getattr(settings, "RAG_LONG_POLICY_CHARS", 8000)
    use_rag = policy_id is not None and len(text) > long_threshold
    policy_text_for_prompt = text
    if use_rag:
        try:
            from app.services.rag_service import retrieve
            top_k = getattr(settings, "RAG_TOP_K", 5)
            chunks = retrieve(
                "compliance rules, obligations, and requirements",
                top_k=top_k,
                policy_id=policy_id,
            )
            if chunks:
                policy_text_for_prompt = "\n\n---\n\n".join(c.get("text", "") for c in chunks)
                policy_text_for_prompt = f"(Excerpts from the policy document.)\n\n{policy_text_for_prompt}"
        except Exception:
            pass

    # Truncate to stay within LLM context limit (avoids "reduce the length of the messages" error)
    max_chars = getattr(settings, "RULE_EXTRACTION_MAX_POLICY_CHARS", MAX_POLICY_CHARS_FOR_EXTRACTION)
    if len(policy_text_for_prompt) > max_chars:
        policy_text_for_prompt = (
            policy_text_for_prompt[: max_chars - 80].rstrip()
            + "\n\n[... policy text truncated for length ...]"
        )
        logger.info("Rule extraction: policy text truncated to %s chars", max_chars)

    system_prompt = """You are a compliance rule extractor. Your output must be strictly valid JSON only: a single JSON array of rule objects. Do not include any explanation, markdown, or text outside the JSON.

Each rule object must have these fields:
- "entity" (string): table/entity name, e.g. "employees"
- "field" (string): column name, e.g. "training_completed"
- "condition" (object or string): structured condition when applicable:
  - For time-based rules (e.g. "within 30 days of X"): use object with "type": "deadline", "days": <number>, "reference_field": "<column name>"
  - For simple equality: use object with "type": "equality"
  - For boolean checks: use object with "type": "boolean"
  - Use string only for free-text description when no structured condition fits
- "operator" (string): "=", "!=", "<", ">", "<=", ">="
- "value" (string, number, or boolean): expected value
- "severity" (string): e.g. "low", "medium", "high"
- "policy_clause_text" (string, optional): exact or paraphrased policy clause from the document

Example rule with deadline:
{"entity": "employees", "field": "training_completed", "condition": {"type": "deadline", "days": 30, "reference_field": "date_of_joining"}, "operator": "=", "value": false, "severity": "medium", "policy_clause_text": "Employees must complete training within 30 days."}"""

    user_prompt = f"""Extract compliance rules from the following policy text. Return only a JSON array of rule objects in the exact format above. Use structured "condition" objects (type "deadline", "equality", or "boolean") and include "policy_clause_text" when you can quote the clause.

Policy text:

{policy_text_for_prompt}"""

    try:
        client = get_completion_client()
        response = client.chat.completions.create(
            model=get_completion_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "invalid_api_key" in err_str or "incorrect api key" in err_str:
            return _fallback_rules_from_text(text)
        if "reduce the length" in err_str or "maximum context" in err_str:
            raise RuleExtractionError(
                "Policy document is too long for the LLM. Try a shorter document or split into smaller files."
            ) from e
        raise RuleExtractionError(f"LLM error (Groq/Llama): {e}") from e

    if not response.choices:
        raise RuleExtractionError("LLM returned no response")
    content = response.choices[0].message.content
    if not content:
        return []

    return _parse_json_safely(content)
