"""Configurable word blocklist for content moderation.

Words are stored lowercase. Matching is case-insensitive substring.
Admin adds variations manually (e.g., 'admin', 'adm1n').
"""

# Blocklist for display names and comment bodies.
# Extend as needed — keep lowercase, ASCII-only.
BLOCKED_WORDS: list[str] = [
    "admin",
    "administrator",
    "moderator",
    "ateliermarie",
    "atelier marie",
]
