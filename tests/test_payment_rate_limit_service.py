import pytest

from app.services.payment_rate_limit_service import (
    CHECKOUT_IP_LIMIT,
    CHECKOUT_SESSION_LIMIT,
    PAY_ON_DELIVERY_IP_LIMIT,
    PAY_ON_DELIVERY_SESSION_LIMIT,
    PAYMENT_STATUS_POLL_LIMIT,
    STRIPE_SESSION_ORDER_LIMIT,
    STRIPE_SESSION_SESSION_LIMIT,
    PaymentRateLimitExceededError,
    assert_stripe_session_rate_limit_available,
    consume_checkout_order_rate_limit,
    consume_pay_on_delivery_rate_limit,
    consume_payment_status_poll_rate_limit,
    consume_stripe_session_rate_limit,
)


@pytest.fixture()
def conn(service_db):
    """Alias the shared pooled psycopg connection as ``conn`` for these tests."""
    return service_db


def test_checkout_limited_after_five_attempts_per_session(conn):
    for index in range(CHECKOUT_SESSION_LIMIT):
        consume_checkout_order_rate_limit(
            conn,
            session_id="session-1",
            ip_address=f"10.0.0.{index}",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_checkout_order_rate_limit(
            conn,
            session_id="session-1",
            ip_address="10.0.0.99",
        )

    assert exc.value.scope == "session"
    count = conn.execute(
        """
        SELECT COUNT(*) AS count FROM payment_rate_limit_events
        WHERE action = 'checkout_order_create' AND scope = 'session' AND key = 'session-1'
        """
    ).fetchone()["count"]
    assert count == CHECKOUT_SESSION_LIMIT


def test_checkout_limited_after_twenty_attempts_per_ip(conn):
    for index in range(CHECKOUT_IP_LIMIT):
        consume_checkout_order_rate_limit(
            conn,
            session_id=f"session-{index}",
            ip_address="203.0.113.9",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_checkout_order_rate_limit(
            conn,
            session_id="session-extra",
            ip_address="203.0.113.9",
        )

    assert exc.value.scope == "ip"
    count = conn.execute(
        """
        SELECT COUNT(*) AS count FROM payment_rate_limit_events
        WHERE action = 'checkout_order_create' AND scope = 'ip' AND key = '203.0.113.9'
        """
    ).fetchone()["count"]
    assert count == CHECKOUT_IP_LIMIT


def test_stripe_session_limited_after_three_attempts_per_order(conn):
    for _ in range(STRIPE_SESSION_ORDER_LIMIT):
        consume_stripe_session_rate_limit(
            conn,
            order_id="order-1",
            session_id="session-1",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_stripe_session_rate_limit(
            conn,
            order_id="order-1",
            session_id="session-1",
        )

    assert exc.value.scope == "order"


def test_stripe_session_limited_after_ten_attempts_per_session(conn):
    for index in range(STRIPE_SESSION_SESSION_LIMIT):
        consume_stripe_session_rate_limit(
            conn,
            order_id=f"order-{index}",
            session_id="session-1",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_stripe_session_rate_limit(
            conn,
            order_id="order-extra",
            session_id="session-1",
        )

    assert exc.value.scope == "session"


def test_stripe_session_precheck_does_not_record_attempt(conn):
    assert_stripe_session_rate_limit_available(conn, session_id="session-1")

    count = conn.execute(
        """
        SELECT COUNT(*) AS count FROM payment_rate_limit_events
        WHERE action = 'stripe_session_create'
        """
    ).fetchone()["count"]
    assert count == 0


def test_pay_on_delivery_limited_after_two_attempts_per_session(conn):
    for index in range(PAY_ON_DELIVERY_SESSION_LIMIT):
        consume_pay_on_delivery_rate_limit(
            conn,
            session_id="session-1",
            ip_address=f"198.51.100.{index}",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_pay_on_delivery_rate_limit(
            conn,
            session_id="session-1",
            ip_address="198.51.100.99",
        )

    assert exc.value.scope == "session"


def test_pay_on_delivery_limited_after_five_attempts_per_ip(conn):
    for index in range(PAY_ON_DELIVERY_IP_LIMIT):
        consume_pay_on_delivery_rate_limit(
            conn,
            session_id=f"session-{index}",
            ip_address="198.51.100.8",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_pay_on_delivery_rate_limit(
            conn,
            session_id="session-extra",
            ip_address="198.51.100.8",
        )

    assert exc.value.scope == "ip"


def test_payment_status_poll_limited_after_sixty_checks_per_session(conn):
    for index in range(PAYMENT_STATUS_POLL_LIMIT):
        consume_payment_status_poll_rate_limit(
            conn,
            session_id="session-1",
            ip_address=f"203.0.113.{index}",
        )

    with pytest.raises(PaymentRateLimitExceededError) as exc:
        consume_payment_status_poll_rate_limit(
            conn,
            session_id="session-1",
            ip_address="203.0.113.99",
        )

    assert exc.value.scope == "session"
