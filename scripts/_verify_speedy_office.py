"""THROWAWAY: confirm full live price with real clientId + serviceId 505.

Uses the real SPEEDY_CLIENT_ID from .env as sender.clientId (now accepted) and a
non-empty serviceIds. Confirms door + office modes both price live. Delete after use.
"""

from __future__ import annotations

import json

import httpx
from pydantic_settings import BaseSettings


class _Creds(BaseSettings):
    speedy_api_username: str = ""
    speedy_api_password: str = ""
    speedy_client_id: str = ""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


BASE = "https://api.speedy.bg/v1"


def _run(label: str, recipient: dict, service_ids: list[int]) -> None:
    c = _Creds()
    payload = {
        "userName": c.speedy_api_username,
        "password": c.speedy_api_password,
        "service": {"serviceIds": service_ids},
        "sender": {"clientId": int(c.speedy_client_id)},
        "recipient": recipient,
        "content": {"parcelsCount": 1, "totalWeight": 0.5},
        "payment": {"courierServicePayer": "RECIPIENT"},
    }
    r = httpx.post(f"{BASE}/calculate", json=payload, timeout=20)
    data = r.json()
    calcs = data.get("calculations") or []
    err = data.get("error")
    print(f"[{label}] {'LIVE ✅' if calcs else 'no-calc'} http={r.status_code}")
    for cc in calcs[:4]:
        print(
            "   serviceId=",
            cc.get("serviceId"),
            "deadline=",
            cc.get("deliveryDeadline"),
            "price=",
            json.dumps(cc.get("price", {}))[:140],
        )
    if err:
        print("   err:", err.get("context"), "|", err.get("message", "")[:70])


def main() -> None:
    _run(
        "DOOR (clientId + 505)",
        {"privatePerson": True, "addressLocation": {"siteName": "София", "postCode": "1000"}},
        [505],
    )
    _run(
        "OFFICE (clientId + pickupOfficeId=1 + 505)",
        {"privatePerson": True, "pickupOfficeId": 1},
        [505],
    )
    # discover ALL services available to this client (omit filter → some API
    # versions return all; if it errors, we already know 505 works).
    _run(
        "DOOR all-services probe (serviceIds absent→will error, informational)",
        {"privatePerson": True, "addressLocation": {"siteName": "София", "postCode": "1000"}},
        [505, 202, 108, 831, 2, 7],
    )


if __name__ == "__main__":
    main()
