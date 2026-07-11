"""Cross-module constants — single source of truth.

Rule: if a value appears in 2+ files, it lives here.
Module-specific constants stay local to their file.
"""

# SQLite-compatible datetime format (no T separator, no timezone suffix)
SQLITE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Session expiry (in days, used to derive seconds in config)
SESSION_MAX_AGE_DAYS = 30
SESSION_ABSOLUTE_LIFETIME_DAYS = 180
SESSION_SLIDING_THRESHOLD_DAYS = 7

# Pagination bounds
MAX_PAGE = 1000
MAX_LIMIT = 100

# Product value bounds (for validation in CSV import and admin endpoints)
MAX_PRICE_CENTS = 99_999_99  # $99,999.99
MAX_STOCK = 999_999
