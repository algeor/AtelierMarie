"""Order, return, product, and COGS integration with inventory ledger mode."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.models.delivery import DeliveryInfo, DeliveryOffice
from app.models.inventory import InventoryValuationSettingsRequest, OpeningBalanceRequest
from app.services import inventory_service, product_service
from app.services.order_service import checkout, get_order_inventory_context, update_status
from app.services.product_service import LedgerManagedStockEditError
from app.services.return_service import create_return_case, inspect_return_case, receive_return_case

_DT_FMT = "%Y-%m-%d %H:%M:%S"


@pytest.fixture()
def ledger_conn(db):
    return db


def _session(conn: psycopg.Connection) -> str:
    session_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO sessions (id, created_at, expires_at) VALUES (%s, %s, %s)",
        (session_id, now.strftime(_DT_FMT), (now + timedelta(days=30)).strftime(_DT_FMT)),
    )
    conn.commit()
    return session_id


def _delivery() -> DeliveryInfo:
    return DeliveryInfo(
        method="office",
        office=DeliveryOffice(
            courier="econt",
            office_id="econt-1029",
            office_name="Sofia",
            office_type="office",
            city="Sofia",
            phone="+359888123456",
        ),
    )


def _seed_product(
    conn: psycopg.Connection,
    product_id: str,
    *,
    stock: int = 10,
    ledger_managed: bool = False,
) -> None:
    conn.execute(
        """
        INSERT INTO products (id, name_en, price_cents, stock, is_active)
        VALUES (%s, %s, 2500, %s, 1)
        """,
        (product_id, product_id.replace("-", " ").title(), stock),
    )
    if ledger_managed:
        conn.execute(
            """
            INSERT INTO product_inventory_profiles (
                product_id, inventory_mode, stock_source,
                opening_balance_state, valuation_readiness
            ) VALUES (%s, 'ledger_managed', 'inventory_ledger', 'reviewed', 'ready')
            """,
            (product_id,),
        )
    conn.commit()


def _add_cart_item(
    conn: psycopg.Connection, session_id: str, product_id: str, quantity: int
) -> None:
    conn.execute(
        "INSERT INTO cart_items (session_id, product_id, quantity) VALUES (%s, %s, %s)",
        (session_id, product_id, quantity),
    )
    conn.commit()


def _movement_rows(conn: psycopg.Connection, product_id: str) -> list[dict]:
    return conn.execute(
        """
        SELECT *
        FROM inventory_movements
        WHERE product_id = %s
        ORDER BY created_at, id
        """,
        (product_id,),
    ).fetchall()


def test_checkout_records_sale_issue_only_for_ledger_managed_products(ledger_conn):
    session_id = _session(ledger_conn)
    _seed_product(ledger_conn, "ledger-candle", stock=10, ledger_managed=True)
    _seed_product(ledger_conn, "legacy-candle", stock=10, ledger_managed=False)
    _add_cart_item(ledger_conn, session_id, "ledger-candle", 2)
    _add_cart_item(ledger_conn, session_id, "legacy-candle", 1)

    order = checkout(
        conn=ledger_conn,
        session_id=session_id,
        customer_email="buyer@example.com",
        customer_name="Buyer",
        delivery=_delivery(),
    )

    assert (
        ledger_conn.execute("SELECT stock FROM products WHERE id = 'ledger-candle'").fetchone()[
            "stock"
        ]
        == 8
    )
    assert (
        ledger_conn.execute("SELECT stock FROM products WHERE id = 'legacy-candle'").fetchone()[
            "stock"
        ]
        == 9
    )

    movements = _movement_rows(ledger_conn, "ledger-candle")
    assert [(row["movement_type"], row["quantity_delta"]) for row in movements] == [
        ("sale_issue", -2.0)
    ]
    assert movements[0]["order_id"] == order["id"]
    assert movements[0]["order_item_key"] == f"{order['id']}:ledger-candle"
    order_movements, order_movement_total = inventory_service.list_inventory_movements(
        order_id=order["id"]
    )
    assert order_movement_total == 1
    assert order_movements[0].id == movements[0]["id"]
    assert _movement_rows(ledger_conn, "legacy-candle") == []


def test_cancellation_reverses_ledger_sale_issue_movement(ledger_conn):
    session_id = _session(ledger_conn)
    _seed_product(ledger_conn, "ledger-candle", stock=10, ledger_managed=True)
    _add_cart_item(ledger_conn, session_id, "ledger-candle", 2)
    order = checkout(
        conn=ledger_conn,
        session_id=session_id,
        customer_email="buyer@example.com",
        customer_name="Buyer",
        delivery=_delivery(),
    )

    update_status(ledger_conn, order["id"], "cancelled")

    movements = _movement_rows(ledger_conn, "ledger-candle")
    sale = next(row for row in movements if row["movement_type"] == "sale_issue")
    reversal = next(row for row in movements if row["movement_type"] == "cancellation_reversal")
    assert reversal["quantity_delta"] == 2.0
    assert reversal["reversal_of_movement_id"] == sale["id"]
    assert (
        ledger_conn.execute("SELECT stock FROM products WHERE id = 'ledger-candle'").fetchone()[
            "stock"
        ]
        == 10
    )


def test_return_inspection_creates_ledger_restock_and_write_off_movements(ledger_conn):
    session_id = _session(ledger_conn)
    _seed_product(ledger_conn, "ledger-candle", stock=10, ledger_managed=True)
    _add_cart_item(ledger_conn, session_id, "ledger-candle", 2)
    order = checkout(
        conn=ledger_conn,
        session_id=session_id,
        customer_email="buyer@example.com",
        customer_name="Buyer",
        delivery=_delivery(),
    )
    case = create_return_case(ledger_conn, order_id=order["id"], reason="customer_return")
    receive_return_case(ledger_conn, case["id"])

    inspect_return_case(
        ledger_conn,
        case["id"],
        restock_decision="partial",
        restock_quantities={"ledger-candle": 1},
        admin_id="admin-1",
        admin_email="owner@example.com",
    )

    assert (
        ledger_conn.execute("SELECT stock FROM products WHERE id = 'ledger-candle'").fetchone()[
            "stock"
        ]
        == 9
    )
    movements = _movement_rows(ledger_conn, "ledger-candle")
    assert sorted(row["movement_type"] for row in movements) == [
        "return_restock",
        "return_restock",
        "return_write_off",
        "sale_issue",
    ]
    assert sorted(row["quantity_delta"] for row in movements) == [-2.0, -1.0, 1.0, 1.0]
    write_off = next(row for row in movements if row["movement_type"] == "return_write_off")
    received_for_write_off = next(
        row
        for row in movements
        if row["movement_type"] == "return_restock"
        and row["id"] == write_off["reversal_of_movement_id"]
    )
    assert received_for_write_off["quantity_delta"] == 1.0
    assert (
        ledger_conn.execute(
            "SELECT exception_type FROM inventory_exceptions WHERE source_id = %s",
            (case["id"],),
        ).fetchone()["exception_type"]
        == "returned_item_write_off_review"
    )


def test_cogs_rows_use_payment_date_source_movement_and_return_reversal(ledger_conn):
    session_id = _session(ledger_conn)
    _seed_product(ledger_conn, "ledger-candle", stock=10, ledger_managed=True)
    inventory_service.update_inventory_valuation_settings(
        InventoryValuationSettingsRequest(
            ledger_mode="setup",
            valuation_enabled=True,
            valuation_method="weighted_average",
            effective_date="2026-09-01",
            cogs_date_basis="payment_date",
            accountant_reviewed=True,
        )
    )
    inventory_service.record_opening_balance(
        OpeningBalanceRequest(
            item_type="finished_good",
            item_id="ledger-candle",
            quantity=10,
            uom="unit",
            unit_value_amount="2.00",
            reviewed=True,
        )
    )
    _add_cart_item(ledger_conn, session_id, "ledger-candle", 2)
    order = checkout(
        conn=ledger_conn,
        session_id=session_id,
        customer_email="buyer@example.com",
        customer_name="Buyer",
        delivery=_delivery(),
    )
    ledger_conn.execute(
        "UPDATE orders SET payment_status = 'paid', paid_at = '2026-09-15 10:00:00' WHERE id = %s",
        (order["id"],),
    )
    ledger_conn.commit()

    inventory_service.generate_valuation_layers()
    cogs = inventory_service.generate_cogs_rows()

    sale_movement = ledger_conn.execute(
        "SELECT id FROM inventory_movements WHERE movement_type = 'sale_issue' AND order_id = %s",
        (order["id"],),
    ).fetchone()
    assert cogs.total == 1
    assert cogs.rows[0].cogs_date == "2026-09-15 10:00:00"
    assert cogs.rows[0].source_movement_id == sale_movement["id"]
    assert cogs.rows[0].source_valuation_layer_id is not None
    assert cogs.rows[0].review_state == "official"
    assert inventory_service.list_cogs_rows(product_id="ledger-candle").total == 1
    assert inventory_service.list_cogs_rows(order_id=order["id"]).total == 1
    assert inventory_service.list_cogs_rows(product_id="other-product").total == 0

    case = create_return_case(ledger_conn, order_id=order["id"], reason="customer_return")
    receive_return_case(ledger_conn, case["id"])
    inspect_return_case(ledger_conn, case["id"], restock_decision="restock")
    ledger_conn.commit()
    inventory_service.generate_valuation_layers()
    reversal = inventory_service.generate_cogs_rows()

    assert reversal.total == 1
    assert reversal.rows[0].review_state == "reversed"
    assert reversal.rows[0].reversal_cogs_id == cogs.rows[0].id
    assert reversal.rows[0].source_movement_id is not None
    assert reversal.rows[0].source_valuation_layer_id is not None


def test_cogs_uses_sale_layer_when_order_depletes_stock_and_cancellation_reverses(ledger_conn):
    session_id = _session(ledger_conn)
    _seed_product(ledger_conn, "deplete-candle", stock=2, ledger_managed=True)
    inventory_service.update_inventory_valuation_settings(
        InventoryValuationSettingsRequest(
            ledger_mode="setup",
            valuation_enabled=True,
            valuation_method="weighted_average",
            effective_date="2026-09-01",
            accountant_reviewed=True,
        )
    )
    inventory_service.record_opening_balance(
        OpeningBalanceRequest(
            item_type="finished_good",
            item_id="deplete-candle",
            quantity=2,
            uom="unit",
            unit_value_amount="2.00",
            reviewed=True,
        )
    )
    _add_cart_item(ledger_conn, session_id, "deplete-candle", 2)
    order = checkout(
        conn=ledger_conn,
        session_id=session_id,
        customer_email="buyer@example.com",
        customer_name="Buyer",
        delivery=_delivery(),
    )

    inventory_service.generate_valuation_layers()
    cogs = inventory_service.generate_cogs_rows()

    assert cogs.total == 1
    assert cogs.rows[0].unit_cost_amount == "2.000000"
    assert cogs.rows[0].total_cost_cents == 400
    assert cogs.rows[0].source_valuation_layer_id is not None

    update_status(ledger_conn, order["id"], "cancelled")
    ledger_conn.commit()
    inventory_service.generate_valuation_layers()
    reversal = inventory_service.generate_cogs_rows()

    cancellation = ledger_conn.execute(
        "SELECT id FROM inventory_movements "
        "WHERE movement_type = 'cancellation_reversal' AND order_id = %s",
        (order["id"],),
    ).fetchone()
    assert reversal.total == 1
    assert reversal.rows[0].review_state == "reversed"
    assert reversal.rows[0].reversal_cogs_id == cogs.rows[0].id
    assert reversal.rows[0].source_movement_id == cancellation["id"]


def test_admin_order_inventory_context_and_product_stock_edit_blocking(ledger_conn):
    session_id = _session(ledger_conn)
    _seed_product(ledger_conn, "ledger-candle", stock=10, ledger_managed=True)
    _add_cart_item(ledger_conn, session_id, "ledger-candle", 1)
    order = checkout(
        conn=ledger_conn,
        session_id=session_id,
        customer_email="buyer@example.com",
        customer_name="Buyer",
        delivery=_delivery(),
    )

    context = get_order_inventory_context(ledger_conn, order["id"])
    item_context = context["items"]["ledger-candle"]

    assert item_context["ledger_managed"] is True
    assert item_context["stock_issue_status"] == "issued"
    assert item_context["source_movement_id"] is not None
    assert context["missing_inventory_movement_count"] == 0

    with pytest.raises(LedgerManagedStockEditError):
        product_service.update_product("ledger-candle", {"stock": 4})

    product = product_service.update_product("ledger-candle", {"name_en": "Ledger Candle Updated"})
    assert product["stock"] == 9
    assert product["ledger_managed"] is True
