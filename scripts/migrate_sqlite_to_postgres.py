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
import sqlite3
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

SKIP_SQLITE_PREFIXES = ("sqlite_", "products_fts_")
SKIP_SQLITE_TABLES = {"products_fts_en", "products_fts_bg", "schema_migrations"}
SKIP_POSTGRES_TABLES = {"alembic_version"}


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
    if not tables:
        return
    query = sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
        sql.SQL(", ").join(sql.Identifier(table) for table in tables)
    )
    conn.execute(query)


def assert_target_empty(conn: psycopg.Connection, tables: list[str]) -> None:
    non_empty = [(table, postgres_count(conn, table)) for table in tables]
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
    batch_size: int,
) -> int:
    if not columns:
        return 0
    quoted_cols = ", ".join(f'"{column}"' for column in columns)
    rows = sqlite_conn.execute(f'SELECT {quoted_cols} FROM "{table}"').fetchall()
    if not rows:
        return 0

    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    copied = 0
    with pg_conn.cursor() as cur:
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            values: list[tuple[Any, ...]] = [
                tuple(row[column] for column in columns) for row in batch
            ]
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
        sqlite_names = sqlite_tables(sqlite_conn)
        pg_names = postgres_tables(pg_conn)
        shared = sqlite_names & pg_names
        ordered = dependency_order(shared, postgres_fk_edges(pg_conn, shared))

        table_columns: dict[str, list[str]] = {}
        print("Migration plan:")
        total = 0
        for table in ordered:
            sqlite_cols = sqlite_columns(sqlite_conn, table)
            pg_cols = set(postgres_columns(pg_conn, table))
            columns = [column for column in sqlite_cols if column in pg_cols]
            table_columns[table] = columns
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
                    sqlite_conn, pg_conn, table, table_columns[table], args.batch_size
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
