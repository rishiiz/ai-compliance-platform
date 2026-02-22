"""Generate human-readable explanations for compliance violations using OpenAI or Groq (Llama 3.3 70B)."""

from app.config import settings
from app.services.llm_client import get_completion_client, get_completion_model


def _rag_excerpts_for_rule(policy_id: int | None, rule_data: dict) -> str:
    """Retrieve policy chunks for this rule and return formatted excerpts string, or empty if unavailable."""
    if policy_id is None:
        return ""
    try:
        from app.services.rag_service import retrieve
        clause = (
            rule_data.get("policy_clause_text")
            if isinstance(rule_data.get("policy_clause_text"), str)
            else ""
        )
        query = clause.strip() or f"compliance rule: {rule_data.get('entity', '')} {rule_data.get('field', '')}"
        top_k = getattr(settings, "RAG_TOP_K", 5)
        chunks = retrieve(query, top_k=top_k, policy_id=policy_id)
        if not chunks:
            return ""
        return "\n\n---\n\n".join(c.get("text", "") for c in chunks)
    except Exception:
        return ""


def generate_violation_explanation(
    rule_data: dict,
    record_snapshot: dict,
    sql_query: str,
    policy_id: int | None = None,
) -> str:
    """
    Generate a short explanation of why this record violates the rule.

    Args:
        rule_data: Rule dict (entity, field, condition, operator, value, severity).
        record_snapshot: The violating row as a dict (evidence).
        sql_query: The SQL that selected this violation.
        policy_id: Optional policy ID for RAG-grounded explanation (retrieve policy excerpts).

    Returns:
        A brief plain-text explanation.
    """
    client = get_completion_client()
    excerpts = _rag_excerpts_for_rule(policy_id, rule_data)
    context = ""
    if excerpts:
        context = f"""Policy excerpts (for context):\n{excerpts}\n\n"""
    prompt = f"""Explain in one or two sentences why this database record violates the compliance rule. Be concise and factual. Base your explanation on the rule and, when provided, the policy excerpts above.

{context}Rule: {rule_data}
Record (violating row): {record_snapshot}
Query used: {sql_query}

Explanation:"""

    response = client.chat.completions.create(
        model=get_completion_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=150,
    )
    content = response.choices[0].message.content
    return (content or "").strip()


def generate_remediation_suggestion(
    rule_data: dict,
    record_snapshot: dict,
    explanation: str,
    policy_id: int | None = None,
) -> str:
    """
    Generate 1-3 concrete remediation steps for this violation.

    Args:
        rule_data: Rule dict (entity, field, condition, operator, value, severity).
        record_snapshot: The violating row as a dict (evidence).
        explanation: The violation explanation (why it violates).
        policy_id: Optional policy ID for RAG-grounded remediation (retrieve policy excerpts).

    Returns:
        Plain-text remediation steps (e.g. bullet list as string).
    """
    client = get_completion_client()
    excerpts = _rag_excerpts_for_rule(policy_id, rule_data)
    context = ""
    if excerpts:
        context = f"""Policy excerpts (for context):\n{excerpts}\n\n"""
    prompt = f"""Given this compliance rule and the violating record, suggest 1-3 concrete remediation steps to fix the violation. Be brief and actionable (e.g. "Update field X to value Y", "Add missing DPA", "Delete or anonymize this record"). When policy excerpts are provided, align steps with policy wording where relevant.

{context}Rule: {rule_data}
Record (violating row): {record_snapshot}
Why it violates: {explanation}

Remediation steps (plain text, short bullets or numbered list):"""

    response = client.chat.completions.create(
        model=get_completion_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=200,
    )
    content = response.choices[0].message.content
    return (content or "").strip()
