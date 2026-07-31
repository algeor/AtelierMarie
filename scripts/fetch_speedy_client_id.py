"""Resolve the numeric Speedy `sender.clientId` for the configured API account.

Speedy's `sender.clientId` is a numeric registered-client/contract identifier,
distinct from the API login (`SPEEDY_API_USERNAME`). It is required for live
quotes and shipment creation — without it, quotes degrade to the flat fallback
(see `app/services/speedy_client.py::_sender_client_id`). This script asks
Speedy's `/client/contract` endpoint for every client on the contract so you can
copy the right `clientId` into `SPEEDY_CLIENT_ID`.

Run this once per environment (demo, then prod) whenever the Speedy account
changes. It reads the SAME credentials the app uses, straight from settings:

    SPEEDY_API_USERNAME, SPEEDY_API_PASSWORD   # in .env

Usage:
    .venv/bin/python scripts/fetch_speedy_client_id.py

Then paste the chosen numeric id into .env:

    SPEEDY_CLIENT_ID=<clientId>
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402  (after sys.path bootstrap)


def main() -> int:
    settings = get_settings()
    username = settings.speedy_api_username
    password = settings.speedy_api_password.get_secret_value()

    if not (username and password):
        print(
            "SPEEDY_API_USERNAME / SPEEDY_API_PASSWORD are not set in .env — "
            "cannot query the contract.",
            file=sys.stderr,
        )
        return 1

    url = f"{settings.speedy_base_url}/client/contract"
    try:
        response = httpx.post(
            url,
            json={"userName": username, "password": password, "language": "EN"},
            timeout=15.0,
        )
        response.raise_for_status()
        clients = response.json().get("clients", [])
    except (httpx.HTTPError, ValueError) as exc:
        print(f"Speedy contract lookup failed: {exc}", file=sys.stderr)
        return 1

    if not clients:
        print("No clients returned for this contract.", file=sys.stderr)
        return 1

    print(f"Speedy clients on account {username} ({settings.speedy_base_url}):\n")
    for client in clients:
        client_id = client.get("clientId")
        address = client.get("address", {})
        where = address.get("fullAddressString", "")
        print(f"  SPEEDY_CLIENT_ID={client_id}    {where}")
    print("\nCopy the numeric clientId of the sending account into .env as SPEEDY_CLIENT_ID.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
