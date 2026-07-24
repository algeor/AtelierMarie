"""Tests for the Jinja2 email renderer: interpolation, loops, conditionals,
locale fallback, both-missing error, and autoescape=False."""

import pytest

from app.email.renderer import TemplateMissingError, render_template

_ITEMS = [
    {"product_name": "Lavender Dream", "quantity": 2, "line_total_display": "€50.00"},
    {"product_name": "Midnight Amber", "quantity": 1, "line_total_display": "€35.00"},
]

_CTX = {
    "order_id_short": "1234abcd",
    "customer_name": "Ben & Co",
    "items": _ITEMS,
    "total_display": "€85.00",
    "customer_email": "ben@example.com",
    "admin_order_url": "https://admin.example/orders/1234abcd",
    "tracking_carrier": "speedy",
    "tracking_number": "77",
    "tracking_url": "https://www.speedy.bg/en/track-shipment?shipmentNumber=77",
}


class TestRendering:
    def test_subject_and_body_split(self):
        subject, body = render_template("placed", "en", _CTX)
        assert subject == "Your Atelier Marie order #1234abcd"
        assert "Lavender Dream" in body
        assert subject not in body

    def test_loop_lists_all_items(self):
        _, body = render_template("placed", "en", _CTX)
        assert "Lavender Dream × 2 — €50.00" in body
        assert "Midnight Amber × 1 — €35.00" in body

    def test_autoescape_off_ampersand_literal(self):
        # Decision 20: plain text must NOT HTML-escape "&".
        _, body = render_template("placed", "en", _CTX)
        assert "Ben & Co" in body
        assert "&amp;" not in body

    def test_conditional_tracking_url_present(self):
        _, body = render_template("shipped", "en", _CTX)
        assert "https://www.speedy.bg" in body

    def test_conditional_tracking_url_omitted(self):
        ctx = {**_CTX, "tracking_url": None}
        _, body = render_template("shipped", "en", ctx)
        assert "Track your package" not in body
        assert "77" in body  # number still shown

    def test_greeting_fallback_no_name(self):
        ctx = {**_CTX, "customer_name": None}
        _, body = render_template("placed", "en", ctx)
        assert "Hi there" in body

    def test_cancelled_mentions_refund(self):
        _, body_en = render_template("cancelled", "en", _CTX)
        assert "refund" in body_en.lower()
        _, body_bg = render_template("cancelled", "bg", _CTX)
        assert "възстановяване" in body_bg.lower()

    def test_bg_locale_used(self):
        subject, _ = render_template("placed", "bg", _CTX)
        assert "Atelier Marie" in subject
        assert "поръчка" in subject.lower()

    def test_admin_new_order_template(self):
        subject, body = render_template("admin_new_order", "en", _CTX)
        assert "1234abcd" in subject
        assert "ben@example.com" in body
        assert "https://admin.example/orders/1234abcd" in body


class TestLocaleFallback:
    def test_missing_bg_falls_back_to_en(self):
        # admin_new_order has no BG template — must fall back to EN.
        subject, body = render_template("admin_new_order", "bg", _CTX)
        assert "1234abcd" in subject

    def test_both_missing_raises(self):
        with pytest.raises(TemplateMissingError):
            render_template("nonexistent_event", "en", _CTX)
