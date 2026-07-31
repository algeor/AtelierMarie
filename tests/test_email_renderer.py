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
    "items_total_display": "€85.00",
    "shipping_display": "€6.50",
    "total_display": "€91.50",
    "customer_email": "ben@example.com",
    "admin_order_url": "https://admin.example/orders/1234abcd",
    "tracking_carrier": "speedy",
    "tracking_number": "77",
    "tracking_url": "https://www.speedy.bg/en/track-shipment?shipmentNumber=77",
    "delivery_method_display": "Door delivery",
    "delivery_courier_display": "Speedy",
    "delivery_lines": [
        "Address: Vitosha, building 1, apt. 5",
        "City/place: 1000 Sofia",
        "Phone: +359888123456",
    ],
    "shipping_is_fallback": True,
    "payment_method": "card",
    "payment_status": "paid",
    "terms_url": "https://shop.example/en/terms",
    "privacy_url": "https://shop.example/en/privacy",
    "cookies_url": "https://shop.example/en/cookies",
    "contact_url": "https://shop.example/en/contact",
    "trader_name": "Atelier Marie",
    "trader_contact_email": "contacts@theateliermarie.com",
    "bank_name": "Test Bank",
    "bank_iban": "BG00TEST",
    "bank_bic": "TESTBGSF",
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

    def test_placed_includes_shipping_and_delivery_details(self):
        _, body = render_template("placed", "en", _CTX)
        assert "Shipping: €6.50 (estimated)" in body
        assert "- Method: Door delivery" in body
        assert "- Courier: Speedy" in body
        assert "- Address: Vitosha, building 1, apt. 5" in body
        assert "- Phone: +359888123456" in body

    def test_shipping_line_does_not_merge_with_following_labels(self):
        cases = [
            ("placed", "en", _CTX, "Shipping: €6.50 (estimated)\nTotal: €91.50"),
            ("payment_pending", "en", _CTX, "Shipping: €6.50 (estimated)\nTotal: €91.50"),
            ("admin_new_order", "en", _CTX, "Shipping: €6.50 (estimated)\nDelivery:"),
            ("placed", "bg", _CTX, "Доставка: €6.50 (ориентировъчна)\nОбщо: €91.50"),
            ("payment_pending", "bg", _CTX, "Доставка: €6.50 (ориентировъчна)\nОбщо: €91.50"),
        ]
        for event, locale, ctx, expected in cases:
            _, body = render_template(event, locale, ctx)
            assert expected in body

    def test_shipping_line_keeps_newline_when_not_estimated(self):
        ctx = {**_CTX, "shipping_is_fallback": False}
        _, body = render_template("placed", "en", ctx)
        assert "Shipping: €6.50\nTotal: €91.50" in body
        assert "€6.50Total" not in body

    def test_autoescape_off_ampersand_literal(self):
        # Decision 20: plain text must NOT HTML-escape "&".
        _, body = render_template("placed", "en", _CTX)
        assert "Ben & Co" in body
        assert "&amp;" not in body

    def test_conditional_tracking_url_present(self):
        _, body = render_template("shipped", "en", _CTX)
        assert "https://www.speedy.bg" in body
        assert "- City/place: 1000 Sofia" in body

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

    def test_bg_placed_includes_localized_delivery_labels(self):
        ctx = {
            **_CTX,
            "delivery_method_display": "До адрес",
            "delivery_lines": ["Адрес: Витоша", "Град/населено място: 1000 София"],
        }
        _, body = render_template("placed", "bg", ctx)
        assert "Доставка: €6.50 (ориентировъчна)" in body
        assert "- Начин: До адрес" in body
        assert "- Адрес: Витоша" in body

    def test_admin_new_order_template(self):
        subject, body = render_template("admin_new_order", "en", _CTX)
        assert "1234abcd" in subject
        assert "ben@example.com" in body
        assert "https://admin.example/orders/1234abcd" in body
        assert "Shipping: €6.50 (estimated)" in body
        assert "- Courier: Speedy" in body

    def test_admin_payment_review_template(self):
        ctx = {
            **_CTX,
            "order_number": "AM-123ABC",
            "payment_review_reason": "reservation_expired",
            "payment_review_stripe_event_id": "evt_review",
            "payment_review_checkout_session_id": "cs_review",
            "payment_review_payment_intent_id": "pi_review",
        }

        subject, body = render_template("admin_payment_review_required", "en", ctx)

        assert "AM-123ABC" in subject
        assert "reservation_expired" in body
        assert "evt_review" in body
        assert "cs_review" in body
        assert "pi_review" in body
        assert "ben@example.com" not in body

    def test_placed_email_includes_legal_references(self):
        _, body = render_template("placed", "en", _CTX)
        assert "https://shop.example/en/terms" in body
        assert "https://shop.example/en/privacy" in body
        assert "contacts@theateliermarie.com" in body
        assert "Lavender Dream" in body

    def test_bg_payment_pending_email_includes_legal_references(self):
        ctx = {
            **_CTX,
            "payment_method": "bank_transfer",
            "terms_url": "https://shop.example/bg/terms",
            "privacy_url": "https://shop.example/bg/privacy",
            "cookies_url": "https://shop.example/bg/cookies",
            "contact_url": "https://shop.example/bg/contact",
        }
        _, body = render_template("payment_pending", "bg", ctx)
        assert "https://shop.example/bg/terms" in body
        assert "https://shop.example/bg/privacy" in body
        assert "BG00TEST" in body
        assert "Lavender Dream" in body


class TestLocaleFallback:
    def test_missing_bg_falls_back_to_en(self):
        # admin_new_order has no BG template — must fall back to EN.
        subject, body = render_template("admin_new_order", "bg", _CTX)
        assert "1234abcd" in subject

    def test_both_missing_raises(self):
        with pytest.raises(TemplateMissingError):
            render_template("nonexistent_event", "en", _CTX)
