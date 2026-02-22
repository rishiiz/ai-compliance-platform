"""Unit tests for schemas and validation."""

import pytest

from app.schemas.rule_data import validate_rule_data


def test_validate_rule_data_equality_ok():
    """Valid equality rule passes."""
    data = {
        "entity": "employees",
        "field": "status",
        "condition": {"type": "equality"},
        "operator": "=",
        "value": "active",
        "severity": "high",
    }
    out = validate_rule_data(data)
    assert out["entity"] == "employees"
    assert out["condition"]["type"] == "equality"


def test_validate_rule_data_boolean_ok():
    """Valid boolean rule passes."""
    data = {
        "entity": "contracts",
        "field": "signed",
        "condition": {"type": "boolean"},
        "operator": "=",
        "value": True,
        "severity": "medium",
    }
    out = validate_rule_data(data)
    assert out["condition"]["type"] == "boolean"


def test_validate_rule_data_deadline_ok():
    """Valid deadline rule passes."""
    data = {
        "entity": "trainings",
        "field": "due_date",
        "condition": {"type": "deadline", "days": 30, "reference_field": "start_date"},
        "operator": "<=",
        "value": None,
        "severity": "low",
    }
    out = validate_rule_data(data)
    assert out["condition"]["type"] == "deadline"
    assert out["condition"]["days"] == 30


def test_validate_rule_data_comparison_ok():
    """Valid comparison rule passes."""
    data = {
        "entity": "orders",
        "field": "amount",
        "condition": {"type": "comparison"},
        "operator": ">",
        "value": 1000,
        "severity": "high",
    }
    out = validate_rule_data(data)
    assert out["condition"]["type"] == "comparison"


def test_validate_rule_data_missing_fields_raises():
    """Missing required fields raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        validate_rule_data({"entity": "x"})
    assert "Missing" in str(exc_info.value) or "required" in str(exc_info.value).lower()


def test_validate_rule_data_not_dict_raises():
    """Non-dict input raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        validate_rule_data([])
    assert "dict" in str(exc_info.value).lower()


def test_validate_rule_data_invalid_condition_type_raises():
    """Invalid condition type raises ValueError."""
    with pytest.raises(ValueError):
        validate_rule_data(
            {
                "entity": "x",
                "field": "y",
                "condition": {"type": "invalid"},
                "operator": "=",
                "value": 1,
                "severity": "low",
            }
        )
