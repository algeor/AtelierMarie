"""Tests for defensive sqlite row access helpers."""

import sqlite3

from app.utils.row_access import row_to_dict_safe, safe_row_get


def _row() -> sqlite3.Row:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT 'vanilla' AS scent, NULL AS label, 3200 AS price_cents"
        ).fetchone()
    finally:
        conn.close()


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
