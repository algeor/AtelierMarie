"""Route tests for public contact submissions."""

import pytest


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
    headers = {"x-forwarded-for": "198.51.100.22"}
    for index in range(5):
        response = await client.post(
            "/v1/contact",
            headers=headers,
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
        headers=headers,
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
