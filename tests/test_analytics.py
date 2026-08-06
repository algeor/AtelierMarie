import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.config import get_settings
from app.database import get_db
from app.services import analytics_service
from app.services.gdpr_service import anonymize_analytics_subject

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module", autouse=True)
def analytics_env(tmp_path_factory, monkeypatch_module):
    tmp = tmp_path_factory.mktemp("analytics")
    monkeypatch_module.setenv("ANALYTICS_ENABLED", "true")
    monkeypatch_module.setenv("ANALYTICS_DATA_DIR", str(tmp))
    monkeypatch_module.setenv("ANALYTICS_EVENTS_JSONL_PATH", str(tmp / "events.jsonl"))
    monkeypatch_module.setenv("ANALYTICS_DUCKDB_PATH", str(tmp / "analytics.duckdb"))
    monkeypatch_module.setenv("ANALYTICS_BATCH_SIZE", "2")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clean_analytics_files():
    settings = get_settings()
    for path in (settings.analytics_events_jsonl_path, settings.analytics_duckdb_path):
        p = Path(path)
        if p.exists():
            p.unlink()
    analytics_service.initialize_storage()
    yield


def event_payload(event_id="evt-test-1", event_type="add_to_cart", **properties):
    default_properties: dict[str, object] = {}
    if event_type == "add_to_cart":
        default_properties = {"product_id": "lavender-dream-300ml", "quantity": 1}
    elif event_type == "product_view":
        default_properties = {"product_id": "lavender-dream-300ml"}
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "locale": "en",
        "page_path": "/products/lavender-dream-300ml",
        "properties": {**default_properties, **properties},
    }


async def grant_analytics_consent(client, analytics=True):
    response = await client.post(
        "/v1/analytics/consent",
        json={
            "analytics": analytics,
            "consent_version": get_settings().analytics_consent_version,
            "locale": "en",
        },
    )
    assert response.status_code == 200
    assert response.json()["analytics"] is analytics


async def test_events_without_server_consent_are_not_persisted(client):
    response = await client.post("/v1/analytics/events", json=event_payload())

    assert response.status_code == 202
    assert response.json()["accepted"] == 0
    assert response.json()["disabled"] is True
    path = Path(get_settings().analytics_events_jsonl_path)
    assert not path.exists() or path.read_text() == ""


async def test_valid_single_event_returns_202_and_writes_jsonl(client):
    await grant_analytics_consent(client)

    response = await client.post("/v1/analytics/events", json=event_payload())

    assert response.status_code == 202
    assert response.json()["accepted"] == 1

    lines = Path(get_settings().analytics_events_jsonl_path).read_text().splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["event_type"] == "add_to_cart"
    assert stored["session_id"]


async def test_event_ingestion_storage_runs_off_loop_thread(client, monkeypatch):
    await grant_analytics_consent(client)
    caller_thread_id = threading.get_ident()
    worker_thread_ids: list[int] = []

    def fake_ingest(events, **_kwargs):
        worker_thread_ids.append(threading.get_ident())
        return {"accepted": len(events), "duplicates": 0, "disabled": False}

    monkeypatch.setattr(analytics_service, "ingest_events", fake_ingest)

    response = await client.post("/v1/analytics/events", json=event_payload("evt-off-loop"))

    assert response.status_code == 202
    assert response.json()["accepted"] == 1
    assert worker_thread_ids and worker_thread_ids[0] != caller_thread_id


async def test_valid_batch_returns_202_and_writes_all_events(client):
    await grant_analytics_consent(client)

    response = await client.post(
        "/v1/analytics/events",
        json={
            "events": [
                event_payload("evt-batch-1"),
                event_payload(
                    "evt-batch-2",
                    event_type="cart_open",
                    item_count=1,
                    value_cents=3200,
                    currency="BGN",
                ),
            ]
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] == 2
    assert len(Path(get_settings().analytics_events_jsonl_path).read_text().splitlines()) == 2


@pytest.mark.parametrize(
    "payload",
    [
        {"event": {**event_payload(), "event_type": "unknown"}},
        {"event": event_payload("evt-pii", email="buyer@example.com")},
        {"event": event_payload("evt-unknown", unexpected="x")},
        {"events": [event_payload("evt-1"), event_payload("evt-2"), event_payload("evt-3")]},
    ],
)
async def test_invalid_payloads_return_422_without_persisting(client, payload):
    response = await client.post("/v1/analytics/events", json=payload)

    assert response.status_code == 422
    path = Path(get_settings().analytics_events_jsonl_path)
    assert not path.exists() or path.read_text() == ""


async def test_duplicate_event_id_is_not_double_counted(client):
    await grant_analytics_consent(client)
    payload = event_payload("evt-duplicate")

    first = await client.post("/v1/analytics/events", json=payload)
    second = await client.post("/v1/analytics/events", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["duplicates"] == 1
    assert len(Path(get_settings().analytics_events_jsonl_path).read_text().splitlines()) == 1


async def test_duckdb_rebuild_from_jsonl_preserves_counts(client):
    await grant_analytics_consent(client)

    await client.post("/v1/analytics/events", json=event_payload("evt-rebuild"))

    analytics_service.rebuild_duckdb_from_jsonl()

    assert analytics_service.count_events_by_type()["add_to_cart"] == 1


async def test_admin_analytics_endpoints_require_admin(client, admin_client):
    denied = await client.get("/v1/admin/analytics/summary")
    allowed = await admin_client.get("/v1/admin/analytics/summary")

    assert denied.status_code in {401, 403}
    assert allowed.status_code == 200
    assert "backend_order_count" in allowed.json()


async def test_admin_analytics_summary_runs_report_off_loop_thread(admin_client, monkeypatch):
    caller_thread_id = threading.get_ident()
    worker_thread_ids: list[int] = []

    def fake_summary(_start_date=None, _end_date=None):
        worker_thread_ids.append(threading.get_ident())
        return {
            "start_date": "2026-08-01",
            "end_date": "2026-08-01",
            "consented_sessions": 0,
            "accepted_events": 0,
            "conversion_rate": 0.0,
            "backend_order_count": 0,
            "backend_revenue_cents": 0,
            "analytics_purchase_count": 0,
            "analytics_purchase_revenue_cents": 0,
            "coverage_percent": 0.0,
            "consented_order_count": 0,
            "consented_order_delta": 0,
            "delivery_warning": False,
            "health": {"retention_days": get_settings().analytics_retention_days},
        }

    monkeypatch.setattr(analytics_service, "get_summary", fake_summary)

    response = await admin_client.get("/v1/admin/analytics/summary")

    assert response.status_code == 200
    assert worker_thread_ids and worker_thread_ids[0] != caller_thread_id


async def test_health_reports_accepted_duplicate_and_validation_failure(client, admin_client):
    await grant_analytics_consent(client)
    payload = event_payload("evt-health")
    await client.post("/v1/analytics/events", json=payload)
    await client.post("/v1/analytics/events", json=payload)
    await client.post(
        "/v1/analytics/events",
        json={"event": event_payload("evt-bad", email="x@y.test")},
    )

    response = await admin_client.get("/v1/admin/analytics/health")

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] >= 1
    assert body["duplicate"] >= 1
    assert body["validation_failure"] >= 1


async def test_order_coverage_warns_for_missing_consented_purchase(
    db_path, admin_client, session_id
):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO orders (
              id, session_id, status, total_cents, customer_email, locale,
              payment_method, payment_status, analytics_consent, created_at, updated_at
            ) VALUES (
              %s, %s, 'pending', 3200, 'buyer@example.com', 'en', 'cod', 'cod_pending', 1,
              CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """,
            ("order-analytics-missing", session_id),
        )

    response = await admin_client.get("/v1/admin/analytics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["backend_order_count"] == 1
    assert body["consented_order_count"] == 1
    assert body["analytics_purchase_count"] == 0
    assert body["delivery_warning"] is True


async def test_gdpr_anonymizes_linked_analytics_identity(client, app):
    await grant_analytics_consent(client)

    await client.post(
        "/v1/analytics/events",
        json={
            "event": event_payload(
                "evt-erase",
                event_type="payment_redirect",
                order_id="order-to-erase",
                payment_method="card",
                payment_provider="stripe",
                value_cents=3200,
                currency="BGN",
            )
        },
    )

    count = anonymize_analytics_subject(order_ids=["order-to-erase"])

    assert count == 1
    assert analytics_service.get_summary()["accepted_events"] == 0


async def test_withdrawing_server_consent_stops_persisting_events(client):
    await grant_analytics_consent(client)
    accepted = await client.post("/v1/analytics/events", json=event_payload("evt-before-withdraw"))
    assert accepted.status_code == 202
    assert accepted.json()["accepted"] == 1

    await grant_analytics_consent(client, analytics=False)
    rejected = await client.post("/v1/analytics/events", json=event_payload("evt-after-withdraw"))

    assert rejected.status_code == 202
    assert rejected.json()["accepted"] == 0
    assert len(Path(get_settings().analytics_events_jsonl_path).read_text().splitlines()) == 1


async def test_retention_cleanup_removes_expired_jsonl_and_duckdb_events(client):
    await grant_analytics_consent(client)
    old_event = event_payload("evt-old-1")
    old_event["occurred_at"] = (datetime.now(UTC) - timedelta(days=400)).isoformat()
    fresh_event = event_payload("evt-fresh")

    await client.post("/v1/analytics/events", json={"events": [old_event, fresh_event]})

    removed = analytics_service.cleanup_expired_events(retention_days=395)

    assert removed == 1
    assert len(Path(get_settings().analytics_events_jsonl_path).read_text().splitlines()) == 1
    assert analytics_service.count_events_by_type()["add_to_cart"] == 1


def test_purchase_analytics_write_failure_is_non_blocking(monkeypatch):
    def fail_ingest(*args, **kwargs):
        raise OSError("analytics disk unavailable")

    monkeypatch.setattr(analytics_service, "ingest_events", fail_ingest)

    analytics_service.record_purchase_confirmed(
        order_id="order-non-blocking",
        session_id="session-non-blocking",
        user_id=None,
        locale="en",
        total_cents=3200,
        payment_method="cod",
        delivery_method="office",
        delivery_courier="speedy",
        analytics_consent=True,
    )
