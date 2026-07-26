"""Taxonomy service — managed product types, categories/tiers, and labels.

Slugs are immutable keys derived server-side from `name_en`. Names are display
data resolved per locale. Deactivating a term hides it from public filters and
new-assignment controls but leaves referencing products intact; hard deletion is
blocked while any product references the term.
"""

import sqlite3
from datetime import UTC, datetime
from typing import Literal

from app.database import get_db
from app.utils.slugify import slugify, unique_slug

# Public kind identifiers used in admin routes (/v1/admin/taxonomy/<kind>).
Kind = Literal["product-types", "categories", "labels"]
Locale = Literal["en", "bg"]

# Per-kind configuration: term table + how products reference the term.
_KIND_TABLE: dict[str, str] = {
    "product-types": "product_types",
    "categories": "product_categories",
    "labels": "product_labels",
}


class TaxonomyNotFoundError(Exception):
    """Raised when a taxonomy term slug does not exist in its table."""


class TaxonomyInUseError(Exception):
    """Raised when deleting a term that products still reference (→ 409)."""


class TaxonomyValidationError(Exception):
    """Raised when a product taxonomy assignment is invalid (→ 422)."""


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _table_for(kind: str) -> str:
    table = _KIND_TABLE.get(kind)
    if table is None:
        raise TaxonomyNotFoundError(f"Unknown taxonomy kind: {kind}")
    return table


def _localized_name(name_en: str, name_bg: str | None, locale: str) -> str:
    """Resolve a display name for a locale, falling back to English."""
    if locale == "bg":
        return name_bg or name_en
    return name_en


# ---------------------------------------------------------------------------
# Product-count helpers (3.5)
# ---------------------------------------------------------------------------


def _counts_for_kind(conn: sqlite3.Connection, kind: str) -> dict[str, int]:
    """Return {slug: in_use_product_count} for every referenced slug of a kind."""
    if kind == "product-types":
        sql = (
            "SELECT product_type_slug AS slug, COUNT(*) AS c "
            "FROM products GROUP BY product_type_slug"
        )
    elif kind == "categories":
        sql = (
            "SELECT category_slug AS slug, COUNT(*) AS c FROM products "
            "WHERE category_slug IS NOT NULL GROUP BY category_slug"
        )
    else:  # labels
        sql = (
            "SELECT label_slug AS slug, COUNT(*) AS c "
            "FROM product_label_assignments GROUP BY label_slug"
        )
    return {row["slug"]: row["c"] for row in conn.execute(sql)}


def _count_one(conn: sqlite3.Connection, kind: str, slug: str) -> int:
    # Counts include soft-deleted (is_active=0) products on purpose: a term ever
    # referenced by any product — even an archived one — must stay for order and
    # history integrity. Such a term can be deactivated but not hard-deleted.
    if kind == "product-types":
        sql = "SELECT COUNT(*) AS c FROM products WHERE product_type_slug = ?"
    elif kind == "categories":
        sql = "SELECT COUNT(*) AS c FROM products WHERE category_slug = ?"
    else:  # labels
        sql = "SELECT COUNT(*) AS c FROM product_label_assignments WHERE label_slug = ?"
    return conn.execute(sql, (slug,)).fetchone()["c"]


# ---------------------------------------------------------------------------
# Public listing (3.1)
# ---------------------------------------------------------------------------


def _public_terms(conn: sqlite3.Connection, table: str, locale: str) -> list[dict]:
    rows = conn.execute(
        f"SELECT slug, name_en, name_bg, sort_order FROM {table} "  # noqa: S608 — table is a constant
        "WHERE is_active = 1 ORDER BY sort_order, slug"
    ).fetchall()
    return [
        {
            "slug": r["slug"],
            "name": _localized_name(r["name_en"], r["name_bg"], locale),
            "sort_order": r["sort_order"],
        }
        for r in rows
    ]


def list_public_taxonomy(locale: Locale = "en") -> dict:
    """Return active taxonomy terms for storefront filter menus, locale-resolved."""
    with get_db() as conn:
        return {
            "product_types": _public_terms(conn, "product_types", locale),
            "categories": _public_terms(conn, "product_categories", locale),
            "labels": _public_terms(conn, "product_labels", locale),
        }


# ---------------------------------------------------------------------------
# Admin CRUD (3.2, 3.3)
# ---------------------------------------------------------------------------


def _term_to_admin_dict(row: sqlite3.Row, product_count: int) -> dict:
    return {
        "slug": row["slug"],
        "name_en": row["name_en"],
        "name_bg": row["name_bg"],
        "sort_order": row["sort_order"],
        "is_active": bool(row["is_active"]),
        "product_count": product_count,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_admin_terms(kind: Kind) -> list[dict]:
    """List all terms of a kind (active and inactive) with in-use product counts."""
    table = _table_for(kind)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} ORDER BY sort_order, slug"  # noqa: S608 — table is a constant
        ).fetchall()
        counts = _counts_for_kind(conn, kind)
    return [_term_to_admin_dict(r, counts.get(r["slug"], 0)) for r in rows]


def get_admin_term(kind: Kind, slug: str) -> dict:
    """Get one term with its in-use product count. Raises TaxonomyNotFoundError."""
    table = _table_for(kind)
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE slug = ?",
            (slug,),  # noqa: S608 — table is a constant
        ).fetchone()
        if row is None:
            raise TaxonomyNotFoundError(f"{kind} not found: {slug}")
        count = _count_one(conn, kind, slug)
    return _term_to_admin_dict(row, count)


def create_term(kind: Kind, name_en: str, name_bg: str | None, sort_order: int) -> dict:
    """Create a taxonomy term with a server-derived unique slug.

    The slug is derived from all existing slugs, then inserted. If a concurrent
    create claims the same slug first, the PRIMARY KEY insert fails; we recompute
    against the now-updated slug set and retry rather than surfacing a 500.
    """
    table = _table_for(kind)
    now = _now_utc()
    with get_db() as conn:
        slug = ""
        for _attempt in range(5):
            existing = {r["slug"] for r in conn.execute(f"SELECT slug FROM {table}")}  # noqa: S608
            slug = unique_slug(slugify(name_en), existing)
            try:
                conn.execute(
                    f"INSERT INTO {table} (slug, name_en, name_bg, sort_order, is_active, "  # noqa: S608
                    "created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (slug, name_en, name_bg, sort_order, now, now),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise TaxonomyValidationError(f"Could not generate a unique slug for: {name_en}")
    return get_admin_term(kind, slug)


def update_term(kind: Kind, slug: str, updates: dict) -> dict:
    """Update a term's name/sort_order/is_active. The slug is immutable.

    `updates` should already exclude unset fields (rename only touches names).
    """
    table = _table_for(kind)
    allowed = {"name_en", "name_bg", "sort_order", "is_active"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if "is_active" in fields:
        fields["is_active"] = 1 if fields["is_active"] else 0

    with get_db() as conn:
        exists = conn.execute(
            f"SELECT 1 FROM {table} WHERE slug = ?",
            (slug,),  # noqa: S608 — table is a constant
        ).fetchone()
        if exists is None:
            raise TaxonomyNotFoundError(f"{kind} not found: {slug}")

        # Products default to a product type and the column is NOT NULL, so the
        # shop must always have at least one active type to assign on create.
        if kind == "product-types" and fields.get("is_active") == 0:
            active_others = conn.execute(
                "SELECT COUNT(*) AS c FROM product_types WHERE is_active = 1 AND slug != ?",
                (slug,),
            ).fetchone()["c"]
            if active_others == 0:
                raise TaxonomyValidationError("Cannot deactivate the last active product type")

        if fields:
            fields["updated_at"] = _now_utc()
            set_clause = ", ".join(f"{col} = ?" for col in fields)
            conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE slug = ?",  # noqa: S608
                [*fields.values(), slug],
            )
    return get_admin_term(kind, slug)


def delete_term(kind: Kind, slug: str) -> None:
    """Hard-delete an unused term. Raises TaxonomyInUseError if referenced.

    "Referenced" counts products regardless of active state (see `_count_one`),
    so a term used by any current or archived product must be deactivated
    instead of deleted.
    """
    table = _table_for(kind)
    with get_db() as conn:
        exists = conn.execute(
            f"SELECT 1 FROM {table} WHERE slug = ?",
            (slug,),  # noqa: S608 — table is a constant
        ).fetchone()
        if exists is None:
            raise TaxonomyNotFoundError(f"{kind} not found: {slug}")
        if _count_one(conn, kind, slug) > 0:
            raise TaxonomyInUseError(
                f"{kind} '{slug}' is in use; reassign or deactivate it before deleting"
            )
        conn.execute(f"DELETE FROM {table} WHERE slug = ?", (slug,))  # noqa: S608


# ---------------------------------------------------------------------------
# Assignment validation (3.4)
# ---------------------------------------------------------------------------


def _term_state(conn: sqlite3.Connection, table: str, slug: str) -> int | None:
    """Return is_active (0/1) for a slug, or None if the slug does not exist."""
    row = conn.execute(
        f"SELECT is_active FROM {table} WHERE slug = ?",
        (slug,),  # noqa: S608 — table is a constant
    ).fetchone()
    return None if row is None else row["is_active"]


def validate_product_type(
    conn: sqlite3.Connection, slug: str, *, current: str | None = None
) -> None:
    """Product type must be an active product type, or equal the current one.

    Passing the product's current (possibly inactive) type is allowed so admins
    can edit unrelated fields without being forced to reclassify.
    """
    if current is not None and slug == current:
        # Confirm the current slug still exists (data integrity), but allow inactive.
        if _term_state(conn, "product_types", slug) is None:
            raise TaxonomyValidationError(f"Unknown product type: {slug}")
        return
    state = _term_state(conn, "product_types", slug)
    if state is None:
        raise TaxonomyValidationError(f"Unknown product type: {slug}")
    if state == 0:
        raise TaxonomyValidationError(f"Product type is not active: {slug}")


def validate_category(
    conn: sqlite3.Connection, slug: str | None, *, current: str | None = None
) -> None:
    """Category may be NULL, an active category, or the product's current one."""
    if slug is None or slug == "":
        return
    if current is not None and slug == current:
        if _term_state(conn, "product_categories", slug) is None:
            raise TaxonomyValidationError(f"Unknown category: {slug}")
        return
    state = _term_state(conn, "product_categories", slug)
    if state is None:
        raise TaxonomyValidationError(f"Unknown category: {slug}")
    if state == 0:
        raise TaxonomyValidationError(f"Category is not active: {slug}")


def validate_labels(
    conn: sqlite3.Connection, slugs: list[str], *, current: set[str] | None = None
) -> None:
    """Each label must be an active label, or already assigned to the product.

    Validates the whole set in a single query (no per-slug round-trips).
    """
    current = current or set()
    unique = list(dict.fromkeys(slugs))
    if not unique:
        return
    placeholders = ", ".join("?" for _ in unique)
    rows = conn.execute(
        f"SELECT slug, is_active FROM product_labels WHERE slug IN ({placeholders})",  # noqa: S608
        unique,
    ).fetchall()
    state = {r["slug"]: r["is_active"] for r in rows}
    for slug in unique:
        st = state.get(slug)
        if st is None:
            raise TaxonomyValidationError(f"Unknown label: {slug}")
        # Inactive labels are allowed only if the product already carries them.
        if st == 0 and slug not in current:
            raise TaxonomyValidationError(f"Label is not active: {slug}")


# ---------------------------------------------------------------------------
# Label assignment (3.7)
# ---------------------------------------------------------------------------


def get_product_label_slugs(conn: sqlite3.Connection, product_id: str) -> list[str]:
    """Return a product's assigned label slugs ordered by the label sort order."""
    rows = conn.execute(
        "SELECT a.label_slug AS slug FROM product_label_assignments a "
        "LEFT JOIN product_labels l ON l.slug = a.label_slug "
        "WHERE a.product_id = ? ORDER BY l.sort_order, a.label_slug",
        (product_id,),
    ).fetchall()
    return [r["slug"] for r in rows]


def replace_product_labels(conn: sqlite3.Connection, product_id: str, slugs: list[str]) -> None:
    """Replace a product's label set within the caller's transaction."""
    conn.execute("DELETE FROM product_label_assignments WHERE product_id = ?", (product_id,))
    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique = [s for s in slugs if not (s in seen or seen.add(s))]
    conn.executemany(
        "INSERT INTO product_label_assignments (product_id, label_slug) VALUES (?, ?)",
        [(product_id, s) for s in unique],
    )


# ---------------------------------------------------------------------------
# Batched display-name resolver (3.6)
# ---------------------------------------------------------------------------


def _name_map(conn: sqlite3.Connection, table: str, slugs: set[str], locale: str) -> dict[str, str]:
    """Map slug → localized name for the given slugs (includes inactive terms)."""
    if not slugs:
        return {}
    placeholders = ", ".join("?" for _ in slugs)
    rows = conn.execute(
        f"SELECT slug, name_en, name_bg FROM {table} WHERE slug IN ({placeholders})",  # noqa: S608
        list(slugs),
    ).fetchall()
    return {r["slug"]: _localized_name(r["name_en"], r["name_bg"], locale) for r in rows}


def resolve_products_taxonomy(
    conn: sqlite3.Connection, products: list[dict], locale: str = "en"
) -> list[dict]:
    """Attach taxonomy display metadata to product dicts without N+1 queries.

    Each product dict must carry `id`, `product_type_slug`, and `category_slug`.
    Adds `product_type`, `product_type_name`, `category` (slug), `category_name`,
    and `labels` ([{slug, name}]). Missing taxonomy rows fall back to the raw slug.
    Inactive referenced terms are resolved too, so retired terms still render.
    """
    if not products:
        return products

    type_slugs = {p["product_type_slug"] for p in products if p.get("product_type_slug")}
    category_slugs = {p["category_slug"] for p in products if p.get("category_slug")}
    product_ids = [p["id"] for p in products]

    type_names = _name_map(conn, "product_types", type_slugs, locale)
    category_names = _name_map(conn, "product_categories", category_slugs, locale)

    # Batched label fetch for all products at once.
    labels_by_product: dict[str, list[dict]] = {pid: [] for pid in product_ids}
    if product_ids:
        placeholders = ", ".join("?" for _ in product_ids)
        rows = conn.execute(
            "SELECT a.product_id, a.label_slug, l.name_en, l.name_bg "
            "FROM product_label_assignments a "
            "LEFT JOIN product_labels l ON l.slug = a.label_slug "
            f"WHERE a.product_id IN ({placeholders}) "  # noqa: S608
            "ORDER BY l.sort_order, a.label_slug",
            product_ids,
        ).fetchall()
        for r in rows:
            name = (
                _localized_name(r["name_en"], r["name_bg"], locale)
                if r["name_en"] is not None
                else r["label_slug"]
            )
            labels_by_product.setdefault(r["product_id"], []).append(
                {"slug": r["label_slug"], "name": name}
            )

    for p in products:
        type_slug = p.get("product_type_slug") or "candles"
        cat_slug = p.get("category_slug")
        p["product_type"] = type_slug
        p["product_type_name"] = type_names.get(type_slug, type_slug)
        p["category"] = cat_slug
        p["category_name"] = category_names.get(cat_slug, cat_slug) if cat_slug else None
        p["labels"] = labels_by_product.get(p["id"], [])
    return products
