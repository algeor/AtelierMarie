#!/usr/bin/env python3
"""Sync Cookie Policy inventory rows from deploy/browser audit JSON.

Reads a JSON object from stdin:
    {"items": [{"name": "...", ...}], "source": "deploy_audit"}

The app-owned registry cookies are always included, because auth/session cookies
may not appear during an anonymous browser crawl.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.database import init_db  # noqa: E402
from app.services import cookies_service  # noqa: E402


def _read_payload() -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid audit JSON: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if not isinstance(payload, dict):
        print("Audit JSON must be an object.", file=sys.stderr)
        raise SystemExit(2)
    return payload


def main() -> int:
    payload = _read_payload()
    settings = get_settings()
    init_db(settings.database_path)

    source = str(payload.get("source") or "deploy_audit")
    provided_items = payload.get("items") or []
    if not isinstance(provided_items, list):
        print("Audit JSON `items` must be an array.", file=sys.stderr)
        return 2

    rows = cookies_service.sync_detected_inventory(
        [*cookies_service.default_detected_inventory(), *provided_items],
        source=source,
        deactivate_missing=True,
    )
    active_rows = [row for row in rows if row["is_active"]]
    print(
        json.dumps(
            {
                "synced": len(rows),
                "active": len(active_rows),
                "names": [row["name"] for row in active_rows],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
