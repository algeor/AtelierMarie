"""Route tests for public contact submissions."""

import pytest

from app.config import Settings
from app.services.contact_service import drain_contact_message_emails


class RecordingProvider:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, *, to, subject, body, reply_to=None, tags=None) -> str:
        self.sent.append(
            {"to": to, "subject": subject, "body": body, "reply_to": reply_to, "tags": tags}
        )
        return "contact-route-msg-1"


def _settings() -> Settings:
    return Settings(
        environment="test",
        email_provider="console",
        email_from_address="orders@theateliermarie.com",
        email_from_name="Atelier Marie",
        email_reply_to="contacts@theateliermarie.com",
        admin_notification_email="contacts@theateliermarie.com",
        frontend_url="https://shop.example",
        jwt_secret="x" * 40,
        admin_api_key="y" * 40,
    )


@pytest.mark.anyio
async def test_valid_contact_submission_persists(client, db):
    response = await client.post(
        "/v1/contact",
        json={
            "name": "Mira",
            "email": "mira@example.com",
            "message": "Do you make custom scents?",
            "locale": "en",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "received"
    assert isinstance(payload["message_id"], int)

    row = db.execute("SELECT name, email_status FROM contact_messages").fetchone()
    assert row["name"] == "Mira"
    assert row["email_status"] == "queued"


@pytest.mark.anyio
async def test_x_forwarded_for_header_is_not_trusted(client, db):
    response = await client.post(
        "/v1/contact",
        headers={"x-forwarded-for": "198.51.100.200"},
        json={
            "name": "Mira",
            "email": "mira@example.com",
            "message": "Hello",
            "locale": "en",
        },
    )

    assert response.status_code == 201
    row = db.execute("SELECT ip_address FROM contact_messages").fetchone()
    assert row["ip_address"]
    assert row["ip_address"] != "198.51.100.200"


@pytest.mark.anyio
async def test_honeypot_returns_success_without_persisting(client, db):
    response = await client.post(
        "/v1/contact",
        json={
            "name": "Bot",
            "email": "bot@example.com",
            "message": "Spam",
            "locale": "en",
            "website": "https://spam.example",
        },
    )

    assert response.status_code == 201
    assert response.json()["message_id"] is None
    count = db.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
    assert count == 0


@pytest.mark.anyio
async def test_missing_fields_return_422(client):
    response = await client.post("/v1/contact", json={"name": "Mira"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_invalid_email_returns_422(client):
    response = await client.post(
        "/v1/contact",
        json={"name": "Mira", "email": "bad", "message": "Hello", "locale": "en"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_invalid_locale_returns_422(client):
    response = await client.post(
        "/v1/contact",
        json={
            "name": "Mira",
            "email": "mira@example.com",
            "message": "Hello",
            "locale": "fr",
        },
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_rate_limit_returns_429(client, db):
    for index in range(5):
        response = await client.post(
            "/v1/contact",
            json={
                "name": f"Mira {index}",
                "email": f"mira{index}@example.com",
                "message": "Hello",
                "locale": "en",
            },
        )
        assert response.status_code == 201

    response = await client.post(
        "/v1/contact",
        json={
            "name": "Mira last",
            "email": "mira-last@example.com",
            "message": "Hello",
            "locale": "en",
        },
    )

    assert response.status_code == 429
    count = db.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
    assert count == 5


@pytest.mark.anyio
async def test_non_json_returns_422(client):
    response = await client.post(
        "/v1/contact",
        content="name=Mira",
        headers={"content-type": "text/plain"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_submit_then_drain_sends_contact_email(client, db):
    response = await client.post(
        "/v1/contact",
        json={
            "name": "Mira",
            "email": "MIRA@EXAMPLE.COM",
            "message": "Do you make custom scents?",
            "locale": "en",
        },
    )
    assert response.status_code == 201

    provider = RecordingProvider()
    processed = drain_contact_message_emails(provider=provider, settings=_settings())

    assert processed == 1
    assert provider.sent[0]["reply_to"] == "mira@example.com"
    row = db.execute("SELECT email, email_status FROM contact_messages").fetchone()
    assert row["email"] == "mira@example.com"
    assert row["email_status"] == "sent"
