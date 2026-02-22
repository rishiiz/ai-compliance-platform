"""
Search the company (external) database for policy content relevant to a user question.
Used by Ask policy: we query the company DB, then send results to Groq for the answer.
Flow: user question -> search company DB -> Groq answers from that content -> output to user.
"""

import logging
import re
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.services.external_db import get_external_engine

logger = logging.getLogger(__name__)


def _safe_identifier(name: str) -> str:
    """Allow only alphanumeric and underscore to prevent SQL injection."""
    if not name or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def search_company_policy_db(query: str, limit: int | None = None) -> list[dict[str, Any]]:
    """
    Search the company database policy table for rows relevant to the user question.
    Uses parameterized ILIKE on the content column (and optional title). Safe against injection.

    Returns:
        List of dicts with keys: content, title (if configured), id (if present).
        Empty list if external DB not connected, table missing, or no matches.
    """
    engine = get_external_engine()
    if engine is None:
        logger.debug("Company policy search skipped: no external database connected.")
        return []

    if not getattr(settings, "USE_COMPANY_DB_FOR_ASK", True):
        return []

    table = _safe_identifier(getattr(settings, "COMPANY_POLICY_TABLE", "policy_documents") or "policy_documents")
    content_col = _safe_identifier(getattr(settings, "COMPANY_POLICY_CONTENT_COLUMN", "content") or "content")
    title_col_raw = (getattr(settings, "COMPANY_POLICY_TITLE_COLUMN", None) or "").strip()
    title_col = _safe_identifier(title_col_raw) if title_col_raw else ""
    limit_val = limit if limit is not None else getattr(settings, "COMPANY_POLICY_SEARCH_LIMIT", 10)
    limit_val = max(1, min(limit_val, 50))

    is_mysql = engine.dialect.name == "mysql"
    quote = "`" if is_mysql else '"'
    cols = [content_col]
    if title_col:
        cols.append(title_col)
    cols.append("id")
    select_cols = ", ".join(f"{quote}{c}{quote}" for c in cols)

    words = [w.strip() for w in (query or "").split() if w.strip()][:10]
    if not words:
        sql = f"SELECT {select_cols} FROM {quote}{table}{quote} ORDER BY id LIMIT :limit"
        params: dict[str, Any] = {"limit": limit_val}
    else:
        if is_mysql:
            conditions = " AND ".join(f"LOWER({quote}{content_col}{quote}) LIKE LOWER(:w{i})" for i in range(len(words)))
        else:
            conditions = " AND ".join(f'{quote}{content_col}{quote} ILIKE :w{i}' for i in range(len(words)))
        sql = f"SELECT {select_cols} FROM {quote}{table}{quote} WHERE {conditions} ORDER BY id LIMIT :limit"
        params = {f"w{i}": f"%{words[i]}%" for i in range(len(words))}
        params["limit"] = limit_val

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
    except Exception as e:
        logger.warning("Company policy search failed: %s", e)
        return []

    out = []
    for row in rows:
        row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(zip(cols, row))
        out.append({
            "content": row_dict.get(content_col) or "",
            "title": row_dict.get(title_col) if title_col else None,
            "id": row_dict.get("id"),
        })
    return out


def get_company_policy_summary(limit: int = 20) -> dict:
    """
    Return a summary of policy content in the company (external) database when connected.
    Used by the dashboard to show username/db and fetched data (count + list of documents).
    Returns: {"connected": True, "count": N, "documents": [{"id", "title"}]} or {"connected": False}.
    """
    engine = get_external_engine()
    if engine is None:
        return {"connected": False}

    table = _safe_identifier(getattr(settings, "COMPANY_POLICY_TABLE", "policy_documents") or "policy_documents")
    content_col = _safe_identifier(getattr(settings, "COMPANY_POLICY_CONTENT_COLUMN", "content") or "content")
    title_col_raw = (getattr(settings, "COMPANY_POLICY_TITLE_COLUMN", None) or "").strip()
    title_col = _safe_identifier(title_col_raw) if title_col_raw else ""
    limit_val = max(1, min(limit, 100))

    is_mysql = engine.dialect.name == "mysql"
    quote = "`" if is_mysql else '"'
    cols = [content_col]
    if title_col:
        cols.append(title_col)
    cols.append("id")
    select_cols = ", ".join(f"{quote}{c}{quote}" for c in cols)

    try:
        with engine.connect() as conn:
            count_sql = f"SELECT COUNT(*) FROM {quote}{table}{quote}"
            total = conn.execute(text(count_sql)).scalar() or 0
            list_sql = f"SELECT {select_cols} FROM {quote}{table}{quote} ORDER BY id LIMIT :lim"
            rows = conn.execute(text(list_sql), {"lim": limit_val}).fetchall()
    except Exception as e:
        err_msg = str(e)
        logger.warning("Company policy summary failed: %s", e)
        if "doesn't exist" in err_msg or "1146" in err_msg or "no such table" in err_msg.lower():
            err_msg = (
                f"Table '{table}' does not exist in your company database. "
                "Create it (see backend/COMPANY_DB_MYSQL_SETUP.sql for MySQL)."
            )
        return {"connected": True, "count": 0, "documents": [], "error": err_msg}

    documents = []
    for row in rows:
        row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(zip(cols, row))
        documents.append({
            "id": row_dict.get("id"),
            "title": row_dict.get(title_col) if title_col else (row_dict.get(content_col) or "")[:80],
        })
    return {"connected": True, "count": total, "documents": documents}
