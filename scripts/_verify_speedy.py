"""THROWAWAY section-0 verification probe for the speedy-integration change.

Reads creds from app settings (never prints them). Runs:
  1. door-mode calculate WITH numeric clientId  -> is price_source live?
  2. office nomenclature endpoint               -> what does a record look like?
  3. /shipment reachability probe (no real create) -> permitted or 403/blocked?

Run:  .venv/bin/python -m scripts._verify_speedy
Delete after use.
"""

from __future__ import annotations

import json
import os

import httpx
from pydantic_settings import BaseSettings


class _ProbeCreds(BaseSettings):
    """Minimal creds reader — ignores unknown .env keys (e.g. the placeholder
    SPEEDY_CLIENT_ID) so the probe runs before the config rename lands."""

    speedy_api_username: str = ""
    speedy_api_password: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def _redact(body: str, limit: int = 800) -> str:
    return body[:limit]


def main() -> None:
    s = _ProbeCreds()
    base = "https://api.speedy.bg/v1"
    user = s.speedy_api_username
    pw = s.speedy_api_password
    # Probe: use the login user as clientId (design open question — does Speedy
    # accept 1996593 as sender.clientId, or require a separate client-object id?).
    raw_client_id = os.environ.get("PROBE_CLIENT_ID", user)
    client_id = int(raw_client_id) if str(raw_client_id).isdigit() else raw_client_id

    print("=== presence (values redacted) ===")
    print("username set:", bool(user))
    print("password set:", bool(pw))
    print("probing clientId == login user:", client_id == (int(user) if user.isdigit() else user))
    print("client_id numeric:", str(client_id).isdigit() if isinstance(client_id, str) else True)
    print()

    # --- 1. door-mode calculate with numeric clientId ---
    calc_payload = {
        "userName": user,
        "password": pw,
        "service": {"serviceIds": []},
        "sender": {"clientId": int(client_id) if str(client_id).isdigit() else client_id},
        "recipient": {
            "privatePerson": True,
            "addressLocation": {"siteName": "София", "postCode": "1000"},
        },
        "content": {"parcelsCount": 1, "totalWeight": 0.5},
        "payment": {"courierServicePayer": "RECIPIENT"},
    }
    print("=== 1. calculate (door, numeric clientId) ===")
    try:
        r = httpx.post(f"{base}/calculate", json=calc_payload, timeout=20)
        print("status:", r.status_code)
        try:
            data = r.json()
        except Exception:
            data = None
        if data is not None:
            calcs = data.get("calculations")
            errs = data.get("error") or data.get("errors")
            print("has calculations:", bool(calcs))
            if calcs:
                print("first calc price:", json.dumps(calcs[0].get("price", {}))[:300])
            if errs:
                print("error field:", json.dumps(errs)[:400])
        print("body(redacted):", _redact(r.text))
    except Exception as exc:
        print("EXC:", type(exc).__name__, str(exc))
    print()

    # --- 2. office nomenclature endpoint ---
    print("=== 2. office nomenclature (location/office) ===")
    off_payload = {"userName": user, "password": pw, "language": "BG", "countryId": 100}
    try:
        r = httpx.post(f"{base}/location/office", json=off_payload, timeout=30)
        print("status:", r.status_code)
        try:
            data = r.json()
        except Exception:
            data = None
        if isinstance(data, dict):
            print("top-level keys:", list(data.keys())[:10])
            offices = data.get("offices") or []
            print("office count:", len(offices))
            if offices:
                print("FIRST OFFICE RECORD:")
                print(json.dumps(offices[0], ensure_ascii=False, indent=2)[:1500])
        else:
            print("body(redacted):", _redact(r.text))
    except Exception as exc:
        print("EXC:", type(exc).__name__, str(exc))
    print()

    # --- 3. /shipment reachability (intentionally minimal; expect a validation error, not 403) ---
    # GUARDED: only runs with PROBE_SHIPMENT=1 because a success creates a real
    # (non-billing) waybill in Speedy's system.
    if os.environ.get("PROBE_SHIPMENT") != "1":
        print("=== 3. /shipment probe SKIPPED (set PROBE_SHIPMENT=1 to run) ===")
        return
    print("=== 3. /shipment permission probe (minimal payload) ===")
    ship_payload = {
        "userName": user,
        "password": pw,
        "service": {"serviceId": 505, "additionalServices": {}},
        "sender": {"clientId": int(client_id) if str(client_id).isdigit() else client_id},
        "recipient": {
            "privatePerson": True,
            "clientName": "Test Recipient",
            "phone1": {"number": "0888112233"},
            "address": {
                "siteName": "София",
                "postCode": "1000",
                "streetName": "Витоша",
                "streetNo": "1",
            },
        },
        "content": {"parcelsCount": 1, "totalWeight": 0.5, "contents": "test", "package": "BOX"},
        "payment": {"courierServicePayer": "SENDER"},
        "ref1": "VERIFY-PROBE",
    }
    try:
        r = httpx.post(f"{base}/shipment", json=ship_payload, timeout=20)
        print("status:", r.status_code)
        print("body(redacted):", _redact(r.text))
    except Exception as exc:
        print("EXC:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()
