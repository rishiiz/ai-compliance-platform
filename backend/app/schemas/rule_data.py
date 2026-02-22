"""Pydantic schemas and validation for rule_data (structured condition format)."""

from typing import Any, Literal, Union

from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError


# --- Condition types (structured only) ---

class ConditionEquality(BaseModel):
    """Condition type: simple equality check."""

    type: Literal["equality"] = "equality"


class ConditionBoolean(BaseModel):
    """Condition type: boolean field check."""

    type: Literal["boolean"] = "boolean"


class ConditionDeadline(BaseModel):
    """Condition type: deadline (e.g. within N days of reference field)."""

    type: Literal["deadline"] = "deadline"
    days: int = Field(..., ge=0, description="Number of days")
    reference_field: str = Field(
        ..., min_length=1, description="Column to measure from (e.g. date_of_joining)"
    )


class ConditionComparison(BaseModel):
    """Condition type: greater than / less than comparison."""

    type: Literal["comparison"] = "comparison"


# Only these four condition types are accepted
ConditionSpec = Union[
    ConditionEquality,
    ConditionBoolean,
    ConditionDeadline,
    ConditionComparison,
]


class RuleDataSchema(BaseModel):
    """
    Validated rule_data structure. All listed fields are required.
    Condition must be a structured object with type one of: equality, boolean, deadline, comparison.
    """

    entity: str = Field(..., min_length=1, description="Table/entity name")
    field: str = Field(..., min_length=1, description="Column name")
    condition: ConditionSpec = Field(
        ...,
        description="Structured condition: type must be equality, boolean, deadline, or comparison",
    )
    operator: str = Field(..., min_length=1, description="Comparison operator (e.g. =, !=, <, >)")
    value: Any = Field(..., description="Expected value (string, number, boolean)")
    severity: str = Field(..., min_length=1, description="Rule severity (e.g. low, medium, high)")
    policy_clause_text: str | None = Field(
        default=None,
        description="Optional human-readable policy clause",
    )

    @field_validator("condition", mode="before")
    @classmethod
    def validate_condition_type(cls, v: Any) -> Any:
        """Ensure condition is a dict with type one of: equality, boolean, deadline, comparison."""
        if isinstance(v, dict):
            t = v.get("type")
            if t not in ("equality", "boolean", "deadline", "comparison"):
                raise ValueError(
                    f"condition.type must be one of: equality, boolean, deadline, comparison; got {t!r}"
                )
        elif not isinstance(v, (ConditionEquality, ConditionBoolean, ConditionDeadline, ConditionComparison)):
            raise ValueError(
                "condition must be a structured object with type: equality, boolean, deadline, or comparison"
            )
        return v


def format_validation_error(e: PydanticValidationError) -> str:
    """Turn Pydantic ValidationError into a clear, readable message."""
    parts = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err.get("msg", "validation error")
        parts.append(f"{loc}: {msg}")
    return "; ".join(parts)


def validate_rule_data(data: dict) -> dict:
    """
    Validate rule_data with Pydantic. Ensures required fields exist and condition type is valid.
    Raises ValueError with a clear message on failure.
    Returns the validated dict for storage.
    """
    if not isinstance(data, dict):
        raise ValueError("rule_data must be a dict")

    required = {"entity", "field", "condition", "operator", "value", "severity"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")

    try:
        model = RuleDataSchema.model_validate(data)
        return model.model_dump(mode="json")
    except PydanticValidationError as e:
        raise ValueError(format_validation_error(e)) from e
