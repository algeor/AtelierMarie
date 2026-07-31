#!/usr/bin/env python3
"""Guarded Econt demo smoke test.

This script verifies demo credentials through Econt getTrace with a deliberately
fake shipment number. It never creates or deletes shipments.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.services.econt_delivery_client import EcontDeliveryClient, EcontDeliveryError  # noqa: E402

DEMO_BASE_URL = "https://delivery-demo.econt.com/services/"
DEMO_HOST = "delivery-demo.econt.com"
PRODUCTION_HOST = "delivery.econt.com"


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").casefold()


def main() -> int:
    if os.environ.get("ECONT_DEMO_SMOKE") != "1":
        print("Refusing to run. Set ECONT_DEMO_SMOKE=1 to confirm this demo-only smoke test.")
        return 2

    settings = get_settings()
    private_key = settings.econt_delivery_private_key.get_secret_value()
    shop_id = settings.econt_delivery_shop_id
    base_url = (settings.econt_delivery_base_url or DEMO_BASE_URL).rstrip("/") + "/"

    missing = []
    if not private_key:
        missing.append("ECONT_DELIVERY_PRIVATE_KEY")
    if not shop_id:
        missing.append("ECONT_DELIVERY_SHOP_ID")
    if missing:
        print("Missing required demo env vars: " + ", ".join(missing))
        return 2

    host = _hostname(base_url)
    if host == PRODUCTION_HOST:
        print(f"Refusing production Econt base URL: {base_url}")
        return 2

    custom_demo_url_allowed = os.environ.get("ECONT_DEMO_ALLOW_CUSTOM_BASE_URL") == "1"
    if host != DEMO_HOST and not custom_demo_url_allowed:
        print(f"Refusing non-demo Econt base URL: {base_url}")
        print("Use ECONT_DEMO_ALLOW_CUSTOM_BASE_URL=1 only for an Econt-approved demo endpoint.")
        return 2

    client = EcontDeliveryClient(
        base_url=base_url,
        private_key=private_key,
        shop_id=shop_id,
    )

    try:
        client.test_connection()
    except EcontDeliveryError as exc:
        safe = exc.to_safe_dict()
        print(f"Econt demo smoke failed: {safe['category']} - {safe['message']}")
        if safe.get("status_code"):
            print(f"HTTP status: {safe['status_code']}")
        return 1

    print("Econt demo smoke passed: credentials reached the safe getTrace validation path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
