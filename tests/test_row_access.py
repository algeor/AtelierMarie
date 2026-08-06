"""Tests for defensive database row access helpers."""

from app.utils.row_access import row_to_dict_safe, safe_row_get


def _row() -> dict[str, object]:
    return {"scent": "vanilla", "label": None, "price_cents": 3200}


def test_safe_row_get_returns_value_for_existing_column():
    row = _row()

    assert safe_row_get(row, "scent") == "vanilla"
    assert safe_row_get(row, "price_cents") == 3200


def test_safe_row_get_returns_default_for_missing_or_null_column():
    row = _row()

    assert safe_row_get(row, "missing", "fallback") == "fallback"
    assert safe_row_get(row, "label", "Untitled") == "Untitled"


def test_row_to_dict_safe_applies_defaults_only_to_null_columns():
    row = _row()

    result = row_to_dict_safe(row, {"label": "Untitled", "scent": "amber"})

    assert result == {
        "scent": "vanilla",
        "label": "Untitled",
        "price_cents": 3200,
    }
