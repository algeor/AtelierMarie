#!/usr/bin/env python3
"""Copy legacy SQLite records into an Alembic-created Postgres database.

Run Alembic first so Postgres has the canonical schema, then run this script.
The script copies only tables and columns that exist in both databases, skips
SQLite internals/FTS shadow tables, orders inserts by Postgres foreign-key
dependencies, and resets identity/serial sequences after import.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

# Postgres data_type values (information_schema.columns) that expect a
# date/time, not a bare number. SQLite stores some of these as epoch-seconds
# strings (e.g. Stripe's created), which Postgres cannot parse as a date.
DATETIME_PG_TYPES = {
    "timestamp with time zone",
    "timestamp without time zone",
    "date",
}
_EPOCH_RE = re.compile(r"^-?\d+(\.\d+)?$")

# Numeric datetime values are only treated as epoch-seconds when they fall in a
# sane range: ~1973 (1e8) to ~2100 (4.1e9). This excludes both YYYYMMDD-style
# integers (e.g. 20260802 ≈ 2e7, below the floor) and 13-digit epoch-millis
# (≈1.7e12, above the ceiling) that would otherwise be misread — or, for millis,
# overflow datetime.fromtimestamp.
_EPOCH_SECONDS_MIN = 100_000_000  # 1973-03-03
_EPOCH_SECONDS_MAX = 4_100_000_000  # 2099-12-xx

SKIP_SQLITE_PREFIXES = ("sqlite_", "products_fts_")
SKIP_SQLITE_TABLES = {"products_fts_en", "products_fts_bg", "schema_migrations"}
SKIP_POSTGRES_TABLES = {"alembic_version"}

# Tables the initial Alembic migration seeds with canonical rows (taxonomy,
# legal/cookies pages, FAQ, delivery/Econt/inventory settings, about content).
# After `alembic upgrade head` these are non-empty, so the default-mode
# "target must be empty" guard must ignore them — otherwise the documented
# happy-path (run Alembic, then this script) always aborts. Inserts use
# ON CONFLICT DO NOTHING so seeded rows are preserved and only non-conflicting
# legacy rows are added; use --truncate to fully replace seeds with legacy data.
# Mirrors the seed-table allowlist in the test harness (tests/conftest.py).
SEEDED_POSTGRES_TABLES = frozenset(
    {
        "product_types",
        "product_categories",
        "product_labels",
        "faq_sections",
        "faq_items",
        "terms_page",
        "terms_sections",
        "privacy_page",
        "privacy_sections",
        "cookies_page",
        "cookies_inventory",
        "cookies_sections",
        "site_banners",
        "delivery_settings",
        "econt_settings",
        "inventory_settings",
        "about_sections",
        "about_items",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate records from the legacy SQLite DB into Postgres."
    )
    parser.add_argument(
        "sqlite_path",
        nargs="?",
        default="atelier_marie.db",
        help="Path to the SQLite database file. Defaults to ./atelier_marie.db.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Postgres DATABASE_URL. Defaults to the DATABASE_URL environment variable.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE migrated Postgres tables before inserting rows.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Allow inserting into non-empty Postgres tables.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned table order and row counts without writing.",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("DATABASE_URL is required; pass --database-url or set it in the environment")
    if args.truncate and args.append:
        parser.error("Use only one of --truncate or --append")
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    return args


def sqlite_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    tables: set[str] = set()
    for row in rows:
        name = row["name"]
        if name in SKIP_SQLITE_TABLES or name.startswith(SKIP_SQLITE_PREFIXES):
            continue
        tables.add(name)
    return tables


def sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [row["name"] for row in rows]


def sqlite_count(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()
    return int(row["count"])


def postgres_tables(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    ).fetchall()
    return {row["tablename"] for row in rows if row["tablename"] not in SKIP_POSTGRES_TABLES}


def postgres_columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return [row["column_name"] for row in rows]


def postgres_datetime_columns(conn: psycopg.Connection, table: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    ).fetchall()
    return {row["column_name"] for row in rows if row["data_type"] in DATETIME_PG_TYPES}


def coerce_datetime_value(value: Any) -> Any:
    """Convert epoch-seconds numbers/strings to aware datetimes; pass the rest through.

    SQLite stores some datetime columns as epoch-seconds (Stripe's created,
    available_on, ...) and others as ISO strings. Postgres parses ISO strings
    natively but rejects a bare epoch number, so only numeric values are
    converted here.
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool is an int subclass — never an epoch
        return value
    if isinstance(value, int | float):
        numeric: float | None = float(value)
    elif isinstance(value, str) and _EPOCH_RE.match(value):
        numeric = float(value)
    else:
        return value
    # Only coerce values in a plausible epoch-seconds range; anything else is
    # left for Postgres to parse (naive ISO strings) or reject with a clear error
    # rather than being silently mapped to a wrong instant.
    if numeric is None or not (_EPOCH_SECONDS_MIN <= abs(numeric) <= _EPOCH_SECONDS_MAX):
        return value
    try:
        return datetime.fromtimestamp(numeric, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return value


def postgres_count(conn: psycopg.Connection, table: str) -> int:
    query = sql.SQL("SELECT COUNT(*) AS count FROM {}").format(sql.Identifier(table))
    return int(conn.execute(query).fetchone()["count"])


def postgres_fk_edges(conn: psycopg.Connection, tables: set[str]) -> dict[str, set[str]]:
    rows = conn.execute(
        """
        SELECT child.relname AS child_table, parent.relname AS parent_table
        FROM pg_constraint c
        JOIN pg_class child ON child.oid = c.conrelid
        JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
        JOIN pg_class parent ON parent.oid = c.confrelid
        JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
        WHERE c.contype = 'f'
          AND child_ns.nspname = 'public'
          AND parent_ns.nspname = 'public'
        """
    ).fetchall()
    edges = {table: set() for table in tables}
    for row in rows:
        child = row["child_table"]
        parent = row["parent_table"]
        if child in tables and parent in tables and child != parent:
            edges[child].add(parent)
    return edges


def dependency_order(tables: set[str], child_to_parents: dict[str, set[str]]) -> list[str]:
    parent_to_children: dict[str, set[str]] = defaultdict(set)
    indegree = {table: len(child_to_parents.get(table, set())) for table in tables}
    for child, parents in child_to_parents.items():
        for parent in parents:
            parent_to_children[parent].add(child)

    ready = deque(sorted(table for table, degree in indegree.items() if degree == 0))
    ordered: list[str] = []
    while ready:
        table = ready.popleft()
        ordered.append(table)
        for child in sorted(parent_to_children[table]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)

    unresolved = sorted(tables - set(ordered))
    if unresolved:
        print(
            "Warning: cyclic or unresolved FK dependency among tables: " + ", ".join(unresolved),
            file=sys.stderr,
        )
        ordered.extend(unresolved)
    return ordered


def truncate_tables(conn: psycopg.Connection, tables: list[str]) -> None:
    # Never truncate Alembic-seeded tables: several hold required config
    # singletons (e.g. inventory_settings id=1). If the legacy SQLite has the
    # table but no rows, truncating would leave the app with no config row and
    # nothing to repopulate it. Their inserts are conflict-tolerant, so legacy
    # rows still merge in while the seeded rows survive.
    targets = [table for table in tables if table not in SEEDED_POSTGRES_TABLES]
    if not targets:
        return
    query = sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
        sql.SQL(", ").join(sql.Identifier(table) for table in targets)
    )
    conn.execute(query)


def assert_target_empty(conn: psycopg.Connection, tables: list[str]) -> None:
    # Alembic-seeded tables are legitimately non-empty after `alembic upgrade
    # head`; excluding them lets the default flow run. Their inserts are
    # conflict-tolerant (see copy_table), so seeds are preserved.
    checked = [table for table in tables if table not in SEEDED_POSTGRES_TABLES]
    non_empty = [(table, postgres_count(conn, table)) for table in checked]
    non_empty = [(table, count) for table, count in non_empty if count > 0]
    if non_empty:
        details = ", ".join(f"{table}={count}" for table, count in non_empty[:20])
        if len(non_empty) > 20:
            details += f", ... {len(non_empty) - 20} more"
        raise RuntimeError(
            "Postgres target is not empty. Re-run with --truncate to replace data "
            f"or --append to allow appending. Non-empty tables: {details}"
        )


def copy_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg.Connection,
    table: str,
    columns: list[str],
    datetime_columns: set[str],
    batch_size: int,
) -> int:
    if not columns:
        return 0
    quoted_cols = ", ".join(f'"{column}"' for column in columns)
    rows = sqlite_conn.execute(f'SELECT {quoted_cols} FROM "{table}"').fetchall()
    if not rows:
        return 0

    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    dt_cols = [column for column in columns if column in datetime_columns]
    copied = 0
    with pg_conn.cursor() as cur:
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            values: list[tuple[Any, ...]] = []
            for row in batch:
                record = {column: row[column] for column in columns}
                for column in dt_cols:
                    record[column] = coerce_datetime_value(record[column])
                values.append(tuple(record[column] for column in columns))
            cur.executemany(insert_query, values)
            copied += len(values)
    return copied


def reset_sequences(conn: psycopg.Connection, tables: list[str]) -> None:
    rows = conn.execute(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
          AND (column_default LIKE 'nextval%%' OR is_identity = 'YES')
        ORDER BY table_name, ordinal_position
        """,
        (tables,),
    ).fetchall()
    for row in rows:
        table = row["table_name"]
        column = row["column_name"]
        max_query = sql.SQL("SELECT MAX({}) AS max_value, COUNT(*) AS count FROM {}").format(
            sql.Identifier(column), sql.Identifier(table)
        )
        stats = conn.execute(max_query).fetchone()
        if stats["count"] == 0 or stats["max_value"] is None:
            continue
        conn.execute(
            "SELECT setval(pg_get_serial_sequence(%s, %s), %s, true)",
            (table, column, stats["max_value"]),
        )


def main() -> int:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        print(f"SQLite database not found: {sqlite_path}", file=sys.stderr)
        return 2

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    with psycopg.connect(args.database_url, row_factory=dict_row) as pg_conn:
        # Pin the session timezone to UTC (mirrors app/database.py). The app writes
        # most timestamps as *naive* UTC strings ("YYYY-MM-DD HH:MM:SS"); those fall
        # through coerce_datetime_value unchanged and Postgres casts the bare text to
        # TIMESTAMPTZ using the session TimeZone GUC. Without this, a server whose
        # default timezone is not UTC would store every naive timestamp at the wrong
        # instant — and inconsistently with the epoch path, which is already UTC-aware.
        pg_conn.execute("SET TIME ZONE 'UTC'")
        sqlite_names = sqlite_tables(sqlite_conn)
        pg_names = postgres_tables(pg_conn)
        shared = sqlite_names & pg_names
        ordered = dependency_order(shared, postgres_fk_edges(pg_conn, shared))

        table_columns: dict[str, list[str]] = {}
        table_datetime_columns: dict[str, set[str]] = {}
        print("Migration plan:")
        total = 0
        for table in ordered:
            sqlite_cols = sqlite_columns(sqlite_conn, table)
            pg_cols = set(postgres_columns(pg_conn, table))
            columns = [column for column in sqlite_cols if column in pg_cols]
            table_columns[table] = columns
            table_datetime_columns[table] = postgres_datetime_columns(pg_conn, table)
            count = sqlite_count(sqlite_conn, table)
            total += count
            skipped = len(sqlite_cols) - len(columns)
            suffix = f" ({skipped} SQLite-only column(s) skipped)" if skipped else ""
            print(f"  {table}: {count} row(s), {len(columns)} column(s){suffix}")

        skipped_tables = sorted(sqlite_names - shared)
        if skipped_tables:
            print("Skipped SQLite tables not present in Postgres: " + ", ".join(skipped_tables))
        print(f"Total SQLite rows planned: {total}")

        if args.dry_run:
            return 0

        try:
            if args.truncate:
                truncate_tables(pg_conn, ordered)
            elif not args.append:
                assert_target_empty(pg_conn, ordered)

            for table in ordered:
                copied = copy_table(
                    sqlite_conn,
                    pg_conn,
                    table,
                    table_columns[table],
                    table_datetime_columns[table],
                    args.batch_size,
                )
                print(f"Copied {copied} row(s) into {table}")
            reset_sequences(pg_conn, ordered)
            pg_conn.commit()
        except Exception:
            pg_conn.rollback()
            raise

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
