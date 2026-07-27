"""Promotion campaign management: CRUD, apply, remove, and status derivation.

Campaigns are management records only — cart, checkout, and public product
pricing never read campaign rows. Applying a campaign writes the discount fields
onto target products using the shared bulk discount logic in
`product_service`, and records the exact values written so removal can be
conservative (see `product_service.conservative_clear_discount`).
"""

import json
import sqlite3
import time
import uuid

import structlog

from app.database import get_db
from app.services import pricing, product_service

logger = structlog.get_logger(__name__)


class CampaignNotFoundError(Exception):
    """Raised when a campaign ID does not exist."""


class CampaignStateError(Exception):
    """Raised when an edit is not allowed in the campaign's current state."""


def _row_to_campaign(row: sqlite3.Row, conn: sqlite3.Connection) -> dict:
    """Map a promotion_campaigns row to the CampaignResponse dict shape.

    `conn` is reused for filter-count resolution so listing many campaigns shares
    one connection (rather than opening one per row); each filter-targeted row
    still runs a product scan to resolve its count.
    """
    target_type = row["target_type"]
    if target_type == "ids":
        target_ids = json.loads(row["target_ids"]) if row["target_ids"] else []
        target_count = len(target_ids)
        target_filter = None
    else:
        target_ids = None
        target_filter = json.loads(row["target_filter"]) if row["target_filter"] else {}
        target_count = len(product_service._resolve_filter_target_ids(conn, target_filter))

    last_result = json.loads(row["last_result"]) if row["last_result"] else None

    return {
        "id": row["id"],
        "name": row["name"],
        "note": row["note"],
        "discount_percent": row["discount_percent"],
        "discount_starts_at": row["discount_starts_at"],
        "discount_ends_at": row["discount_ends_at"],
        "target_type": target_type,
        "target_count": target_count,
        "target_ids": target_ids,
        "target_filter": target_filter,
        "status": _derive_status(row),
        "applied_at": row["applied_at"],
        "removed_at": row["removed_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_result": last_result,
    }


def _derive_status(row: sqlite3.Row) -> str:
    """Derive a campaign's status from its window and applied/removed metadata.

    - removed: discount has been removed after being applied
    - scheduled: the discount window has not started yet (applied or not — a
      freshly created future-dated campaign reads as `scheduled` per spec)
    - ended: applied, and the discount window has already ended
    - active: applied and currently within (or without) a window
    - draft: created, not yet applied (and not future-dated)
    """
    if row["removed_at"] is not None:
        return "removed"

    now = pricing.now_utc()
    starts_at = row["discount_starts_at"]
    ends_at = row["discount_ends_at"]
    if starts_at is not None and now < starts_at:
        return "scheduled"
    if ends_at is not None and now > ends_at and row["applied_at"] is not None:
        # A never-applied past-window campaign is still a draft, not `ended`.
        return "ended"
    if row["applied_at"] is not None:
        return "active"
    return "draft"


def _get_campaign_row(conn: sqlite3.Connection, campaign_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM promotion_campaigns WHERE id = ?",
        (campaign_id,),
    ).fetchone()
    if row is None:
        raise CampaignNotFoundError(f"Campaign not found: {campaign_id}")
    return row


def create_campaign(data: dict) -> dict:
    """Create a campaign management record. Does not change any product."""
    campaign_id = str(uuid.uuid4())
    product_ids = data.get("product_ids")
    filt = data.get("filter")
    if product_ids is not None:
        target_type = "ids"
        target_ids = json.dumps(list(dict.fromkeys(product_ids)))
        target_filter = None
    else:
        target_type = "filter"
        target_ids = None
        target_filter = json.dumps(filt)

    now = pricing.now_utc()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO promotion_campaigns ("
            "id, name, note, discount_percent, discount_starts_at, discount_ends_at, "
            "target_type, target_ids, target_filter, created_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                campaign_id,
                data["name"],
                data.get("note"),
                data["discount_percent"],
                data.get("discount_starts_at"),
                data.get("discount_ends_at"),
                target_type,
                target_ids,
                target_filter,
                now,
                now,
            ),
        )
        row = _get_campaign_row(conn, campaign_id)
        return _row_to_campaign(row, conn)


def update_campaign(campaign_id: str, data: dict) -> dict:
    """Partially update a campaign's metadata, discount, or target.

    Only keys present in `data` are changed. Name/note are editable at any time.
    Discount and target edits are only allowed while the campaign is not
    currently *live* — i.e. it has not been applied, or has since been removed.
    Editing a live campaign's discount/target would desync the displayed campaign
    from the products it actually wrote, so the admin must remove it first and
    re-apply. Switching target source clears the other source so exactly one
    remains stored.
    """
    with get_db() as conn:
        row = _get_campaign_row(conn, campaign_id)

        # Reject clearing the (mandatory) campaign percent — the column is NOT
        # NULL, so a raw write would 500. Surface a 422 instead.
        if "discount_percent" in data and data["discount_percent"] is None:
            raise product_service.DiscountValidationError(
                "discount_percent is required for a campaign"
            )

        # Validate the merged discount window (percent required with dates,
        # start before end) using the effective values after the update. Run
        # request validation (422) before the state-conflict guard (409).
        merged_percent = data.get("discount_percent", row["discount_percent"])
        merged_starts = data.get("discount_starts_at", row["discount_starts_at"])
        merged_ends = data.get("discount_ends_at", row["discount_ends_at"])
        product_service._validate_merged_discount(merged_percent, merged_starts, merged_ends)

        discount_or_target_keys = {
            "discount_percent",
            "discount_starts_at",
            "discount_ends_at",
            "product_ids",
            "filter",
        }
        # Presence of the key counts as an edit — an explicit null must not slip
        # past the guard and silently desync a live campaign's window.
        touches_live_fields = any(k in data for k in discount_or_target_keys)
        # Block discount/target edits only while the campaign is *live* — applied
        # and not yet removed. A never-applied campaign (draft or scheduled) has
        # written no product discounts, so it stays freely editable.
        is_live = row["applied_at"] is not None and row["removed_at"] is None
        if touches_live_fields and is_live:
            raise CampaignStateError(
                "discount and target can only be edited before a campaign is applied "
                "(or after it is removed); remove the campaign first, then re-apply"
            )

        fields: list[str] = []
        params: list = []

        for key in ("name", "note", "discount_percent", "discount_starts_at", "discount_ends_at"):
            if key in data:
                fields.append(f"{key} = ?")
                params.append(data[key])

        if "product_ids" in data and data["product_ids"] is not None:
            fields.append("target_type = ?")
            params.append("ids")
            fields.append("target_ids = ?")
            params.append(json.dumps(list(dict.fromkeys(data["product_ids"]))))
            fields.append("target_filter = ?")
            params.append(None)
        elif "filter" in data and data["filter"] is not None:
            fields.append("target_type = ?")
            params.append("filter")
            fields.append("target_filter = ?")
            params.append(json.dumps(data["filter"]))
            fields.append("target_ids = ?")
            params.append(None)

        if fields:
            fields.append("updated_at = ?")
            params.append(pricing.now_utc())
            params.append(campaign_id)
            conn.execute(
                f"UPDATE promotion_campaigns SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
                params,
            )
        row = _get_campaign_row(conn, campaign_id)
        return _row_to_campaign(row, conn)


def list_campaigns() -> tuple[list[dict], int]:
    """Return all campaigns, newest first, with total count (single connection)."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM promotion_campaigns ORDER BY created_at DESC").fetchall()
        return [_row_to_campaign(r, conn) for r in rows], len(rows)


def get_campaign(campaign_id: str) -> dict:
    """Return one campaign by ID. Raises CampaignNotFoundError if missing."""
    with get_db() as conn:
        row = _get_campaign_row(conn, campaign_id)
        return _row_to_campaign(row, conn)


def delete_campaign(campaign_id: str) -> None:
    """Delete a campaign record. Applied product discounts are left untouched."""
    with get_db() as conn:
        _get_campaign_row(conn, campaign_id)  # 404 if missing
        conn.execute("DELETE FROM promotion_campaigns WHERE id = ?", (campaign_id,))


def _resolve_targets(conn: sqlite3.Connection, row: sqlite3.Row) -> list[str]:
    """Resolve a campaign row's target definition to a capped list of IDs.

    Raises `product_service.BulkTargetLimitError` if the set exceeds the cap.
    Runs on the caller's connection so it composes inside one transaction.
    """
    if row["target_type"] == "ids":
        resolved = list(dict.fromkeys(json.loads(row["target_ids"]) if row["target_ids"] else []))
    else:
        filt = json.loads(row["target_filter"]) if row["target_filter"] else {}
        resolved = product_service._resolve_filter_target_ids(conn, filt)

    if len(resolved) > product_service.BULK_DISCOUNT_TARGET_LIMIT:
        raise product_service.BulkTargetLimitError(
            f"target resolves to {len(resolved)} products; "
            f"limit is {product_service.BULK_DISCOUNT_TARGET_LIMIT}"
        )
    return resolved


def apply_campaign(campaign_id: str) -> dict:
    """Apply a campaign's discount to its resolved target products.

    Resolves targets at apply time, enforces the 500-product cap, then writes the
    discount, records the resolved IDs and exact applied values, and stores the
    result summary — all in ONE transaction so a crash cannot leave products
    discounted without a matching campaign record. `applied_at` is only set when
    at least one product was updated.
    """
    started = time.monotonic()
    with get_db() as conn:
        row = _get_campaign_row(conn, campaign_id)
        target_ids = _resolve_targets(conn, row)

        result = product_service.bulk_update_discount(
            operation="apply",
            product_ids=target_ids,
            discount_percent=row["discount_percent"],
            discount_starts_at=row["discount_starts_at"],
            discount_ends_at=row["discount_ends_at"],
            conn=conn,
        )

        updated_ids = [r["id"] for r in result["results"] if r["status"] == "updated"]
        # Replace prior applied-target records with this apply's successes — but
        # only when this apply actually wrote something. A zero-success re-apply
        # must NOT wipe the records of products still carrying the prior discount,
        # or `remove_campaign` could never clear them (orphaned discount).
        if updated_ids:
            conn.execute(
                "DELETE FROM promotion_campaign_products WHERE campaign_id = ?",
                (campaign_id,),
            )
            for pid in updated_ids:
                conn.execute(
                    "INSERT INTO promotion_campaign_products ("
                    "campaign_id, product_id, applied_percent, applied_starts_at, applied_ends_at"
                    ") VALUES (?, ?, ?, ?, ?)",
                    (
                        campaign_id,
                        pid,
                        row["discount_percent"],
                        row["discount_starts_at"],
                        row["discount_ends_at"],
                    ),
                )

        now = pricing.now_utc()
        if updated_ids:
            # Only transition to applied when at least one product actually changed.
            conn.execute(
                "UPDATE promotion_campaigns SET applied_at = ?, removed_at = NULL, "
                "updated_at = ?, last_result = ? WHERE id = ?",
                (now, now, json.dumps(result), campaign_id),
            )
        else:
            conn.execute(
                "UPDATE promotion_campaigns SET updated_at = ?, last_result = ? WHERE id = ?",
                (now, json.dumps(result), campaign_id),
            )

    logger.info(
        "campaign_applied",
        campaign_id=campaign_id,
        target_count=len(target_ids),
        success_count=result["success_count"],
        failure_count=result["failure_count"],
        duration_ms=round((time.monotonic() - started) * 1000, 1),
    )
    return result


def remove_campaign(campaign_id: str) -> dict:
    """Conservatively clear a campaign's discount from its applied products.

    Only products whose current discount fields still match the campaign's last
    applied values are cleared; edited products are skipped with a warning. The
    clears and the `removed_at`/result write run in ONE transaction. `removed_at`
    is set once every applied target was either cleared or safely skipped.
    """
    started = time.monotonic()
    with get_db() as conn:
        _get_campaign_row(conn, campaign_id)  # 404 if missing
        target_rows = conn.execute(
            "SELECT product_id, applied_percent, applied_starts_at, applied_ends_at "
            "FROM promotion_campaign_products WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchall()

        targets = [
            {
                "product_id": t["product_id"],
                "applied_percent": t["applied_percent"],
                "applied_starts_at": t["applied_starts_at"],
                "applied_ends_at": t["applied_ends_at"],
            }
            for t in target_rows
        ]
        result = product_service.conservative_clear_discount(targets, conn=conn)

        now = pricing.now_utc()
        remove_completed = bool(targets) and all(
            item["status"] in {"updated", "skipped"} for item in result["results"]
        )
        if remove_completed:
            conn.execute(
                "UPDATE promotion_campaigns SET removed_at = ?, updated_at = ?, "
                "last_result = ? WHERE id = ?",
                (now, now, json.dumps(result), campaign_id),
            )
        else:
            # No applied targets, or at least one target failed unexpectedly. Keep
            # the campaign live so the admin can retry after fixing the failure.
            conn.execute(
                "UPDATE promotion_campaigns SET updated_at = ?, last_result = ? WHERE id = ?",
                (now, json.dumps(result), campaign_id),
            )

    logger.info(
        "campaign_removed",
        campaign_id=campaign_id,
        target_count=len(targets),
        success_count=result["success_count"],
        failure_count=result["failure_count"],
        duration_ms=round((time.monotonic() - started) * 1000, 1),
    )
    return result
