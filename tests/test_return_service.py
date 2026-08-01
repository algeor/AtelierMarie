"""Tests for admin-controlled return case service behavior."""

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.database import init_db
from app.services.return_service import (
    InvalidRestockQuantityError,
    InvalidReturnTransitionError,
    InvalidReturnValueError,
    close_return_case,
    cod_settlement_required_for_order,
    create_return_case,
    get_return_case,
    get_cod_settlement_for_order,
    inspect_return_case,
    list_return_cases_for_order,
    record_cod_settlement,
    receive_return_case,
    update_return_accounting,
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def conn(tmp_path):
    path = str(tmp_path / "returns.db")
    init_db(path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    yield connection
    connection.close()


@pytest.fixture()
def order_id(conn: sqlite3.Connection) -> str:
    now = datetime.now(UTC)
    session_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
        (session_id, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
        "VALUES ('candle-a', 'Candle A', 2000, 8, 1)"
    )
    conn.execute(
        "INSERT INTO products (id, name_en, price_cents, stock, is_active) "
        "VALUES ('candle-b', 'Candle B', 1500, 4, 1)"
    )
    conn.execute(
        """
        INSERT INTO orders (
            id, session_id, status, total_cents, customer_email,
            payment_method, payment_status
        ) VALUES (?, ?, 'return_in_transit', 5500, 'return@example.com', 'card', 'paid')
        """,
        (order_id, session_id),
    )
    conn.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (?, 'candle-a', 'Candle A', 2000, 2)
        """,
        (order_id,),
    )
    conn.execute(
        """
        INSERT INTO order_items (order_id, product_id, product_name, price_cents, quantity)
        VALUES (?, 'candle-b', 'Candle B', 1500, 1)
        """,
        (order_id,),
    )
    conn.commit()
    return order_id


def _stock(conn: sqlite3.Connection, product_id: str) -> int:
    return conn.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()[0]


def test_create_return_case_records_case_and_event(conn, order_id):
    case = create_return_case(
        conn,
        order_id=order_id,
        reason="not_picked_up",
        source="admin",
        status="return_in_transit",
        courier_return_fee_cents=500,
        notes="Customer did not collect from office",
        admin_id="admin-1",
        admin_email="owner@example.com",
    )

    assert case["order_id"] == order_id
    assert case["reason"] == "not_picked_up"
    assert case["status"] == "return_in_transit"
    assert case["restock_decision"] == "pending"
    assert case["courier_return_fee_cents"] == 500
    event = conn.execute(
        "SELECT event_type, source, admin_user_id, admin_email, payload_json "
        "FROM order_return_events WHERE order_return_id = ?",
        (case["id"],),
    ).fetchone()
    assert event["event_type"] == "return_created"
    assert event["source"] == "admin"
    assert event["admin_user_id"] == "admin-1"
    assert event["admin_email"] == "owner@example.com"
    assert "not_picked_up" in event["payload_json"]


def test_create_return_case_rejects_invalid_reason_without_event(conn, order_id):
    with pytest.raises(InvalidReturnValueError):
        create_return_case(conn, order_id=order_id, reason="exchange")

    case_count = conn.execute("SELECT COUNT(*) FROM order_returns").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM order_return_events").fetchone()[0]
    assert case_count == 0
    assert event_count == 0


def test_receive_return_case_does_not_restock(conn, order_id):
    case = create_return_case(
        conn,
        order_id=order_id,
        reason="customer_return",
        status="return_in_transit",
    )

    received = receive_return_case(conn, case["id"], admin_id="admin-1")

    assert received["status"] == "received"
    assert received["received_at"] is not None
    assert _stock(conn, "candle-a") == 8
    assert _stock(conn, "candle-b") == 4
    event_types = [
        row[0]
        for row in conn.execute(
            "SELECT event_type FROM order_return_events WHERE order_return_id = ? ORDER BY created_at",
            (case["id"],),
        ).fetchall()
    ]
    assert event_types == ["return_created", "return_received"]


def test_inspect_return_case_restock_adds_stock_and_adjustment_rows(conn, order_id):
    case = create_return_case(conn, order_id=order_id, reason="customer_return")
    receive_return_case(conn, case["id"])

    inspected = inspect_return_case(
        conn,
        case["id"],
        restock_decision="restock",
        notes="Items unopened",
        admin_id="admin-1",
    )

    assert inspected["status"] == "inspected"
    assert inspected["restock_decision"] == "restock"
    assert _stock(conn, "candle-a") == 10
    assert _stock(conn, "candle-b") == 5
    adjustments = conn.execute(
        "SELECT product_id, quantity, reason FROM inventory_adjustments "
        "WHERE order_return_id = ? ORDER BY product_id",
        (case["id"],),
    ).fetchall()
    assert [(row[0], row[1], row[2]) for row in adjustments] == [
        ("candle-a", 2, "return_restock"),
        ("candle-b", 1, "return_restock"),
    ]


def test_inspect_return_case_partial_restock_is_bounded(conn, order_id):
    case = create_return_case(conn, order_id=order_id, reason="customer_return")
    receive_return_case(conn, case["id"])

    with pytest.raises(InvalidRestockQuantityError):
        inspect_return_case(
            conn,
            case["id"],
            restock_decision="partial",
            restock_quantities={"candle-b": 2},
        )

    current = get_return_case(conn, case["id"])
    assert current["status"] == "received"
    assert _stock(conn, "candle-b") == 4
    adjustment_count = conn.execute("SELECT COUNT(*) FROM inventory_adjustments").fetchone()[0]
    assert adjustment_count == 0


def test_inspect_return_case_do_not_restock_records_decision_without_stock_change(conn, order_id):
    case = create_return_case(conn, order_id=order_id, reason="damaged_by_courier")
    receive_return_case(conn, case["id"])

    inspected = inspect_return_case(
        conn,
        case["id"],
        restock_decision="do_not_restock",
        notes="Wax melted in transit",
    )

    assert inspected["status"] == "inspected"
    assert inspected["restock_decision"] == "do_not_restock"
    assert _stock(conn, "candle-a") == 8
    assert conn.execute("SELECT COUNT(*) FROM inventory_adjustments").fetchone()[0] == 0


def test_invalid_return_transitions_are_rejected(conn, order_id):
    case = create_return_case(conn, order_id=order_id, reason="customer_return")

    with pytest.raises(InvalidReturnTransitionError):
        inspect_return_case(conn, case["id"], restock_decision="restock")

    current = get_return_case(conn, case["id"])
    assert current["status"] == "requested"


def test_close_return_case_after_inspection(conn, order_id):
    case = create_return_case(conn, order_id=order_id, reason="customer_return")
    receive_return_case(conn, case["id"])
    inspect_return_case(conn, case["id"], restock_decision="do_not_restock")

    closed = close_return_case(conn, case["id"], admin_email="owner@example.com")

    assert closed["status"] == "closed"
    assert closed["closed_at"] is not None
    listed = list_return_cases_for_order(conn, order_id)
    assert [item["id"] for item in listed] == [case["id"]]


def test_delivered_cod_order_requires_settlement_until_recorded(conn, order_id):
    conn.execute(
        "UPDATE orders SET status = 'delivered', payment_method = 'cod' WHERE id = ?",
        (order_id,),
    )
    conn.commit()

    assert cod_settlement_required_for_order(conn, order_id) is True

    settlement = record_cod_settlement(
        conn,
        order_id=order_id,
        amount_cents=5500,
        settlement_date="2026-08-01",
        courier_reference="COD-123",
        notes="Paid by courier",
        admin_id="admin-1",
    )

    assert settlement["amount_cents"] == 5500
    assert settlement["mismatch_review"] == 0
    assert settlement["created_by_admin_id"] == "admin-1"
    assert cod_settlement_required_for_order(conn, order_id) is False
    assert get_cod_settlement_for_order(conn, order_id)["courier_reference"] == "COD-123"


def test_cod_settlement_amount_mismatch_is_flagged(conn, order_id):
    conn.execute(
        "UPDATE orders SET status = 'delivered', payment_method = 'cod' WHERE id = ?",
        (order_id,),
    )
    conn.commit()

    settlement = record_cod_settlement(
        conn,
        order_id=order_id,
        amount_cents=5000,
        settlement_date="2026-08-01",
    )

    assert settlement["mismatch_review"] == 1


def test_cod_settlement_rejects_non_cod_order(conn, order_id):
    conn.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
    conn.commit()

    with pytest.raises(InvalidReturnValueError):
        record_cod_settlement(
            conn,
            order_id=order_id,
            amount_cents=5500,
            settlement_date="2026-08-01",
        )


def test_update_return_accounting_records_fee_claim_and_event(conn, order_id):
    case = create_return_case(conn, order_id=order_id, reason="damaged_by_courier")

    updated = update_return_accounting(
        conn,
        case["id"],
        courier_return_fee_cents=650,
        courier_claim_id="CLM-123",
        courier_claim_status="filed",
        courier_claim_amount_cents=2500,
        notes="Courier damage claim filed manually",
        admin_id="admin-1",
        admin_email="owner@example.com",
    )

    assert updated["courier_return_fee_cents"] == 650
    assert updated["courier_claim_id"] == "CLM-123"
    assert updated["courier_claim_status"] == "filed"
    assert updated["courier_claim_amount_cents"] == 2500
    event = conn.execute(
        "SELECT event_type, admin_email, payload_json FROM order_return_events "
        "WHERE order_return_id = ? ORDER BY created_at DESC LIMIT 1",
        (case["id"],),
    ).fetchone()
    assert event["event_type"] == "return_accounting_updated"
    assert event["admin_email"] == "owner@example.com"
    assert "CLM-123" in event["payload_json"]
