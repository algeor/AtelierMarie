"""Tests for the guarded Econt demo smoke script."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from pydantic import SecretStr


def _load_smoke_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "econt_demo_smoke.py"
    spec = importlib.util.spec_from_file_location("econt_demo_smoke_test_module", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _settings(*, private_key: str = "", shop_id: str = "", base_url: str = ""):
    return SimpleNamespace(
        econt_delivery_private_key=SecretStr(private_key),
        econt_delivery_shop_id=shop_id,
        econt_delivery_base_url=base_url,
    )


def test_demo_smoke_requires_explicit_guard(monkeypatch, capsys):
    smoke = _load_smoke_module()
    monkeypatch.delenv("ECONT_DEMO_SMOKE", raising=False)
    monkeypatch.setattr(
        smoke,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("settings should not be read")),
    )

    assert smoke.main() == 2

    assert "ECONT_DEMO_SMOKE=1" in capsys.readouterr().out


def test_demo_smoke_requires_credentials(monkeypatch, capsys):
    smoke = _load_smoke_module()
    monkeypatch.setenv("ECONT_DEMO_SMOKE", "1")
    monkeypatch.setattr(smoke, "get_settings", lambda: _settings())
    monkeypatch.setattr(
        smoke,
        "EcontDeliveryClient",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("client should not be built")),
    )

    assert smoke.main() == 2

    out = capsys.readouterr().out
    assert "ECONT_DELIVERY_PRIVATE_KEY" in out
    assert "ECONT_DELIVERY_SHOP_ID" in out


def test_demo_smoke_refuses_production_url_even_with_custom_override(monkeypatch, capsys):
    smoke = _load_smoke_module()
    monkeypatch.setenv("ECONT_DEMO_SMOKE", "1")
    monkeypatch.setenv("ECONT_DEMO_ALLOW_CUSTOM_BASE_URL", "1")
    monkeypatch.setattr(
        smoke,
        "get_settings",
        lambda: _settings(
            private_key="private-demo-key",
            shop_id="shop-1",
            base_url="https://delivery.econt.com/services/",
        ),
    )
    monkeypatch.setattr(
        smoke,
        "EcontDeliveryClient",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("client should not be built")),
    )

    assert smoke.main() == 2

    assert "Refusing production Econt base URL" in capsys.readouterr().out


def test_demo_smoke_uses_safe_connection_check_on_demo_url(monkeypatch, capsys):
    smoke = _load_smoke_module()
    calls: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, base_url, private_key, shop_id):
            calls["base_url"] = base_url
            calls["private_key"] = private_key
            calls["shop_id"] = shop_id

        async def test_connection(self):
            calls["tested"] = True
            return True

    monkeypatch.setenv("ECONT_DEMO_SMOKE", "1")
    monkeypatch.delenv("ECONT_DEMO_ALLOW_CUSTOM_BASE_URL", raising=False)
    monkeypatch.setattr(
        smoke,
        "get_settings",
        lambda: _settings(private_key="private-demo-key", shop_id="shop-1"),
    )
    monkeypatch.setattr(smoke, "EcontDeliveryClient", FakeClient)

    assert smoke.main() == 0

    assert calls == {
        "base_url": "https://delivery-demo.econt.com/services/",
        "private_key": "private-demo-key",
        "shop_id": "shop-1",
        "tested": True,
    }
    assert "passed" in capsys.readouterr().out
