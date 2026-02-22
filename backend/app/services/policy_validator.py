"""AI compliance validation agent for uploaded policy documents."""

import json
import logging
import re
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)

# Minimum compliance score to consider a policy valid
COMPLIANCE_THRESHOLD = 0.65

VALIDATION_SYSTEM_PROMPT = """You are a senior compliance officer and legal expert.
Your task is to review a policy document and assess its compliance quality.

Evaluate the policy on these criteria:
1. Clarity – Is the language clear and unambiguous?
2. Completeness – Does it cover scope, responsibilities, enforcement, and review cycle?
3. Legal alignment – Does it reference relevant regulations (GDPR, HIPAA, ISO 27001, etc.) where applicable?
4. Enforceability – Are rules actionable and measurable?
5. Data protection – Does it properly address data handling, retention, and access control?

Respond ONLY with a valid JSON object in this exact format (no markdown, no extra text):
{
  "compliance_score": <float 0.0-1.0>,
  "is_compliant": <true if score >= 0.65, else false>,
  "summary": "<2-3 sentence summary of what this policy covers>",
  "issues": [<list of specific compliance issues found, empty if none>],
  "suggestions": [<list of specific, actionable improvement suggestions, empty if none>]
}"""


@dataclass
class ValidationResult:
    """Result of AI compliance validation for a single policy document."""
    is_compliant: bool
    compliance_score: float          # 0.0 – 1.0
    summary: str                     # brief AI summary
    issues: list[str] = field(default_factory=list)       # compliance violations
    suggestions: list[str] = field(default_factory=list)  # AI-suggested fixes
    error: str = ""                  # set if validation itself failed


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON object from LLM response, handling markdown code fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Try finding first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def validate_policy_compliance(text: str, filename: str) -> ValidationResult:
    """
    Use the Groq LLM to assess whether a policy document meets compliance standards.

    Args:
        text: Extracted plain text of the policy document.
        filename: Original filename (for context in the prompt).

    Returns:
        ValidationResult with compliance status, score, issues, and suggestions.
    """
    if not text or not text.strip():
        return ValidationResult(
            is_compliant=False,
            compliance_score=0.0,
            summary="No content could be extracted from this file.",
            issues=["The document contains no readable text."],
            suggestions=["Ensure the file is not corrupted and contains readable policy text."],
        )

    # Truncate very long policies — LLMs have context limits
    max_chars = 12_000
    policy_excerpt = text[:max_chars]
    if len(text) > max_chars:
        policy_excerpt += f"\n\n[... document truncated at {max_chars} chars for analysis ...]"

    user_content = f"""Document filename: {filename}

Policy text:
---
{policy_excerpt}
---

Analyze the policy document above and respond with the JSON compliance assessment."""

    try:
        from app.services.llm_client import get_completion_client, get_completion_model
        client = get_completion_client()
        model = get_completion_model()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        raw_answer = (response.choices[0].message.content or "").strip() if response.choices else ""
        logger.debug("Policy validation raw LLM response for %s: %s", filename, raw_answer[:300])

        data = _extract_json_from_response(raw_answer)
        if not data:
            logger.warning("Policy validation: could not parse LLM JSON for %s", filename)
            return ValidationResult(
                is_compliant=False,
                compliance_score=0.0,
                summary="Could not parse compliance assessment from AI response.",
                issues=["AI response was not valid JSON."],
                suggestions=["Try re-uploading the document. If the issue persists, check the server logs."],
                error=f"Raw response: {raw_answer[:200]}",
            )

        score = float(data.get("compliance_score", 0.0))
        score = max(0.0, min(1.0, score))  # clamp to [0, 1]
        is_compliant = score >= COMPLIANCE_THRESHOLD

        return ValidationResult(
            is_compliant=is_compliant,
            compliance_score=round(score, 3),
            summary=str(data.get("summary", "")).strip(),
            issues=[str(i).strip() for i in (data.get("issues") or []) if i],
            suggestions=[str(s).strip() for s in (data.get("suggestions") or []) if s],
        )

    except Exception as e:
        logger.error("Policy validation LLM call failed for %s: %s", filename, e)
        return ValidationResult(
            is_compliant=False,
            compliance_score=0.0,
            summary="Validation failed due to an internal error.",
            issues=["Could not connect to the AI validation service."],
            suggestions=["Check that GROQ_API_KEY is set correctly in backend .env."],
            error=str(e),
        )
