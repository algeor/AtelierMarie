"""THROWAWAY: probe alternative Speedy `sender` shapes for the demo account.

The demo login (1996593) and the portal-displayed client number (8888...) are
both rejected as sender.client.inactive. Speedy's calculate can also take the
sender as a dropoff office or a site/address instead of a registered clientId.
Try several shapes; report which yields calculations.

Reads creds from .env (never prints them). Delete after use.
"""

from __future__ import annotations

import json

import httpx
from pydantic_settings import BaseSettings


class _Creds(BaseSettings):
    speedy_api_username: str = ""
    speedy_api_password: str = ""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


BASE = "https://api.speedy.bg/v1"


def _run(label: str, sender: dict, service: dict | None = None) -> None:
    c = _Creds()
    payload = {
        "userName": c.speedy_api_username,
        "password": c.speedy_api_password,
        "service": service if service is not None else {"serviceIds": []},
        "sender": sender,
        "recipient": {
            "privatePerson": True,
            "addressLocation": {"siteName": "София", "postCode": "1000"},
        },
        "content": {"parcelsCount": 1, "totalWeight": 0.5},
        "payment": {"courierServicePayer": "RECIPIENT"},
    }
    try:
        r = httpx.post(f"{BASE}/calculate", json=payload, timeout=20)
        data = r.json()
        calcs = data.get("calculations") or []
        err = data.get("error")
        status = "LIVE ✅" if calcs else "no-calc"
        print(f"[{label}] {status} http={r.status_code}")
        if calcs:
            for cc in calcs[:6]:
                print(
                    "   serviceId=", cc.get("serviceId"),
                    "price=", json.dumps(cc.get("price", {}))[:120],
                )
        if err:
            print("   err:", err.get("context"), "|", err.get("message", "")[:80])
    except Exception as exc:
        print(f"[{label}] EXC {type(exc).__name__}: {exc}")


def main() -> None:
    dropoff = {"dropoffOfficeId": 1}
    # No serviceIds filter → Speedy should return ALL available services (this is
    # how you discover valid service ids). Some API versions want the key omitted
    # entirely rather than an empty list.
    _run("dropoff + no service key", dropoff, service={})
    _run("dropoff + serviceIds omitted", dropoff, service=None)
    # Common Speedy service ids: 505 (standard 24h), 202, 831 (to office). Try a few.
    for sid in (505, 202, 831, 108):
        _run(f"dropoff + serviceId={sid}", dropoff, service={"serviceIds": [sid]})


if __name__ == "__main__":
    main()
