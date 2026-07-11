"""Defensive row-access helper for sqlite3.Row transformations.

Provides safe attribute access with explicit defaults, avoiding KeyError
crashes when database schema evolves or columns are unexpectedly NULL.
"""

import sqlite3
from typing import Any


def safe_row_get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    """Safely extract a value from a sqlite3.Row, returning default if missing.

    Unlike dict(row)[key], this never raises KeyError for missing columns.
    Useful in service-layer transformations where schema may evolve.

    Args:
        row: A sqlite3.Row instance.
        key: Column name to extract.
        default: Value to return if the column is missing or None.

    Returns:
        The column value, or default if the column doesn't exist or is None.
    """
    try:
        value = row[key]
    except (IndexError, KeyError):
        return default
    return value if value is not None else default


def row_to_dict_safe(row: sqlite3.Row, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert a sqlite3.Row to a dict, applying defaults for None values.

    Args:
        row: A sqlite3.Row instance.
        defaults: Optional mapping of column_name → default_value.
            If a column's value is None and the column has a default,
            the default is substituted.

    Returns:
        A plain dict with all columns from the row.
    """
    result = dict(row)
    if defaults:
        for key, default_value in defaults.items():
            if key in result and result[key] is None:
                result[key] = default_value
    return result
