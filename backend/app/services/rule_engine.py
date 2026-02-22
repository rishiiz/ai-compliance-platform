"""Compile compliance rules to SQL predicates and execute them on the external DB."""

import re
from typing import Any

from sqlalchemy import text

from app.services.external_db import get_external_engine

# Operators: normalized to SQL symbols
_OP_MAP = {
    "eq": "=",
    "equals": "=",
    "=": "=",
    "ne": "!=",
    "!=": "!=",
    "neq": "!=",
    "not_equals": "!=",
    "lt": "<",
    "<": "<",
    "gt": ">",
    ">": ">",
    "lte": "<=",
    "<=": "<=",
    "gte": ">=",
    ">=": ">=",
}

# Values treated as SQL booleans
_BOOL_TRUE = {"true", "yes", "1", "on"}
_BOOL_FALSE = {"false", "no", "0", "off"}

# Loose ISO date pattern (YYYY-MM-DD or with time)
_DATE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}(T|\s|$)"
)

# Bind parameter names (values passed as parameters, not string-concatenated)
_P_VALUE = "p_value"
_P_DAYS = "p_days"


def _quote_identifier(name: str) -> str:
    """Quote and escape a SQL identifier (table/column) for PostgreSQL. Prevents injection."""
    if not name:
        raise ValueError("Identifier cannot be empty")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        raise ValueError(f"Invalid identifier: {name}")
    return f'"{name}"'


def _normalize_bound_value(value: Any) -> Any:
    """Normalize value for bound parameter (safe to pass to execute())."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    lower = s.lower()
    if lower in _BOOL_TRUE:
        return True
    if lower in _BOOL_FALSE:
        return False
    return s


def _is_deadline_rule(operator: str, value: Any) -> bool:
    """Treat as deadline rule when operator is comparison and value looks like date."""
    op = (operator or "").strip().lower()
    if op not in ("<", ">", "<=", ">=", "lt", "gt", "lte", "gte"):
        return False
    if value is None:
        return False
    s = str(value).strip()
    return bool(_DATE_PATTERN.match(s))


def _is_boolean_value(value: Any) -> bool:
    """Return True if value should be treated as SQL boolean."""
    if isinstance(value, bool):
        return True
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in _BOOL_TRUE or s in _BOOL_FALSE


def _to_sql_bool(value: Any) -> bool:
    """Convert a boolean-like value to Python bool for SQL IS TRUE/FALSE (PostgreSQL requires bool, not 0/1)."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in _BOOL_TRUE:
        return True
    if s in _BOOL_FALSE:
        return False
    return bool(value)


def _compile_deadline_condition(
    qualified_field: str,
    ref_qualified: str,
    days: int,
    value: Any,
    op_sql: str,
) -> tuple[str, dict[str, Any]]:
    """
    Compile structured deadline: (field = value) OR (CURRENT_DATE - reference_field::date <= days).
    Returns (predicate_sql, params) with bound :p_value and :p_days.
    """
    params: dict[str, Any] = {_P_VALUE: _to_sql_bool(value) if _is_boolean_value(value) else _normalize_bound_value(value), _P_DAYS: int(days)}
    if _is_boolean_value(value):
        pred = f"({qualified_field} IS :{_P_VALUE} OR (CURRENT_DATE - ({ref_qualified})::date <= :{_P_DAYS}))"
    else:
        pred = f"({qualified_field} {op_sql} :{_P_VALUE} OR (CURRENT_DATE - ({ref_qualified})::date <= :{_P_DAYS}))"
    return pred, params


def compile_rule_to_sql(rule_json: dict) -> tuple[str, dict[str, Any]]:
    """
    Compile a single rule to a parameterized SQL predicate and bind parameters.

    Supports:
    1. Equality checks: field = :p_value
    2. Boolean checks: field IS :p_value (true/false)
    3. Date deadline (structured): (field = :p_value OR (CURRENT_DATE - ref::date <= :p_days))
    4. Greater/less than: field < :p_value, field > :p_value, etc.

    Identifiers (entity, field, reference_field) are validated and quoted; never passed as params.
    Literal values are passed via the parameters dict for safe execution.

    Returns:
        (sql_predicate, parameters) for use in WHERE. NOT (predicate) = violations.
    """
    entity = (rule_json.get("entity") or "").strip()
    field = (rule_json.get("field") or "").strip()
    operator = (rule_json.get("operator") or "=").strip()
    value = rule_json.get("value")
    condition = rule_json.get("condition")

    if not entity or not field:
        raise ValueError("rule_json must contain non-empty entity and field")

    op_sql = _OP_MAP.get(operator.lower(), "=")
    table = _quote_identifier(entity)
    column = _quote_identifier(field)
    qualified = f"{table}.{column}"
    # Use actual bool for IS :p_value so PostgreSQL gets IS TRUE/FALSE, not IS 0/1
    params: dict[str, Any] = {_P_VALUE: _to_sql_bool(value) if _is_boolean_value(value) else _normalize_bound_value(value)}

    # 3. Structured deadline: (field = value) OR (CURRENT_DATE - reference_field::date <= days)
    if isinstance(condition, dict) and (condition.get("type") or "").lower() == "deadline":
        ref = (condition.get("reference_field") or "").strip()
        days = condition.get("days", 0)
        if not ref:
            raise ValueError("Structured deadline condition must have reference_field")
        if not isinstance(days, (int, float)) or days < 0:
            days = 0
        days = int(days)
        ref_qualified = f"{table}.{_quote_identifier(ref)}"
        return _compile_deadline_condition(
            qualified, ref_qualified, days, value, op_sql
        )

    # 2. Boolean checks: field IS :p_value
    if _is_boolean_value(value):
        if op_sql == "=":
            return f"{qualified} IS :{_P_VALUE}", params
        if op_sql == "!=":
            return f"({qualified} IS NOT :{_P_VALUE} OR {qualified} IS NULL)", params
        return f"{qualified} {op_sql} :{_P_VALUE}", params

    # 4. Date deadline (legacy): value is date literal -> use param
    if _is_deadline_rule(operator, value):
        return f"{qualified} {op_sql} :{_P_VALUE}", params

    # 1. Equality and 4. Greater/less than: field op :p_value
    return f"{qualified} {op_sql} :{_P_VALUE}", params


def get_rule_query(rule_json: dict) -> tuple[str, dict[str, Any]]:
    """
    Return the full parameterized SQL query (violating rows) and parameters.

    Returns:
        (sql_query, parameters) for safe execution. Store sql_query in Violation.sql_query.
    """
    predicate, params = compile_rule_to_sql(rule_json)
    entity = (rule_json.get("entity") or "").strip()
    if not entity:
        raise ValueError("rule_json must contain non-empty entity")
    table = _quote_identifier(entity)
    query = f'SELECT * FROM {table} WHERE NOT ({predicate})'
    return query, params


class RuleExecutionError(Exception):
    """Raised when rule execution fails (no engine or DB error)."""

    pass


def _row_to_dict(row: Any) -> dict:
    """Convert a result row to a JSON-friendly dict (e.g. datetime -> isoformat)."""
    if hasattr(row, "_mapping"):
        raw = dict(row._mapping)
    elif hasattr(row, "keys"):
        raw = {k: row[k] for k in row.keys()}
    else:
        raw = dict(row)
    out = {}
    for k, v in raw.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif type(v).__name__ == "Decimal":
            out[k] = float(v)
        else:
            out[k] = v
    return out


def get_entity_count(rule_json: dict) -> int | None:
    """
    Return total row count for the rule's entity (table). Used as rows_scanned metric.
    Returns None if engine not set or query fails.
    """
    engine = get_external_engine()
    if engine is None:
        return None
    entity = (rule_json.get("entity") or "").strip()
    if not entity:
        return None
    try:
        table = _quote_identifier(entity)
        query = f"SELECT COUNT(*) AS c FROM {table}"
        with engine.connect() as conn:
            row = conn.execute(text(query)).fetchone()
            return int(row[0]) if row else None
    except Exception:
        return None


def execute_rule(rule_json: dict) -> list[dict]:
    """
    Compile the rule to parameterized SQL, run it on the external DB, and return violating rows.

    Uses bound parameters for safe execution (no SQL injection from rule values).
    Violating rows are those that do NOT satisfy the rule predicate.
    """
    engine = get_external_engine()
    if engine is None:
        raise RuleExecutionError("No external database connected. Call POST /database/connect first.")

    query, parameters = get_rule_query(rule_json)

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), parameters)
            rows = result.mappings().fetchall()
            return [_row_to_dict(r) for r in rows]
    except Exception as e:
        raise RuleExecutionError(f"Rule execution failed: {e}") from e
