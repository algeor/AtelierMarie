"""Promotion campaign management: CRUD, apply, remove, and status derivation.

Campaigns are management records only — cart, checkout, and public product
pricing never read campaign rows. Applying a campaign writes the discount fields
onto target products using the shared bulk discount logic in
`product_service`, and records the exact values written so removal can be
conservative (see `product_service.conservative_clear_discount`).
"""

import json
import uuid

import structlog

from app.database import get_db
from app.services import pricing, product_service

logger = structlog.get_logger(__name__)


class CampaignNotFoundError(Exception):
    """Raised when a campaign ID does not exist."""


def _row_to_campaign(row, *, last_result: dict | None = None) -> dict:
    """Map a promotion_campaigns row to the CampaignResponse dict shape."""
    target_type = row["target_type"]
    if target_type == "ids":
        target_ids = json.loads(row["target_ids"]) if row["target_ids"] else []
        target_count = len(target_ids)
    else:
        target_count = _resolved_filter_count(row["target_filter"])

    return {
        "id": row["id"],
        "name": row["name"],
        "note": row["note"],
        "discount_percent": row["discount_percent"],
        "discount_starts_at": row["discount_starts_at"],
        "discount_ends_at": row["discount_ends_at"],
        "target_type": target_type,
        "target_count": target_count,
        "status": _derive_status(row),
        "applied_at": row["applied_at"],
        "removed_at": row["removed_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_result": last_result,
    }


def _resolved_filter_count(target_filter: str | None) -> int:
    """Best-effort resolved product count for a filter-targeted campaign."""
    if not target_filter:
        return 0
    filt = json.loads(target_filter)
    with get_db() as conn:
        return len(product_service._resolve_filter_target_ids(conn, filt))


def _derive_status(row) -> str:
    """Derive a campaign's status from its applied/removed metadata + window.

    - removed: discount has been removed after being applied
    - draft: never applied
    - scheduled: applied but the discount window has not started yet
    - ended: applied but the discount window has already ended
    - active: applied and currently within (or without) a window
    """
    if row["removed_at"] is not None:
        return "removed"
    if row["applied_at"] is None:
        return "draft"

    now = pricing.now_utc()
    starts_at = row["discount_starts_at"]
    ends_at = row["discount_ends_at"]
    if starts_at is not None and now < starts_at:
        return "scheduled"
    if ends_at is not None and now > ends_at:
        return "ended"
    return "active"


def _get_campaign_row(conn, campaign_id: str):
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
    return _row_to_campaign(row)


def update_campaign(campaign_id: str, data: dict) -> dict:
    """Partially update a campaign's metadata, discount, or target.

    Only keys present in `data` are changed. Switching target source clears the
    other source so exactly one remains stored.
    """
    with get_db() as conn:
        row = _get_campaign_row(conn, campaign_id)

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

        # Validate the merged discount window (percent required with dates,
        # start before end) using the effective values after the update.
        merged_percent = data.get("discount_percent", row["discount_percent"])
        merged_starts = data.get("discount_starts_at", row["discount_starts_at"])
        merged_ends = data.get("discount_ends_at", row["discount_ends_at"])
        product_service._validate_merged_discount(merged_percent, merged_starts, merged_ends)

        if fields:
            fields.append("updated_at = ?")
            params.append(pricing.now_utc())
            params.append(campaign_id)
            conn.execute(
                f"UPDATE promotion_campaigns SET {', '.join(fields)} WHERE id = ?",  # noqa: S608
                params,
            )
        row = _get_campaign_row(conn, campaign_id)
    return _row_to_campaign(row)


def list_campaigns() -> tuple[list[dict], int]:
    """Return all campaigns, newest first, with total count."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM promotion_campaigns ORDER BY created_at DESC").fetchall()
    return [_row_to_campaign(r) for r in rows], len(rows)


def get_campaign(campaign_id: str) -> dict:
    """Return one campaign by ID. Raises CampaignNotFoundError if missing."""
    with get_db() as conn:
        row = _get_campaign_row(conn, campaign_id)
    return _row_to_campaign(row)


def delete_campaign(campaign_id: str) -> None:
    """Delete a campaign record. Applied product discounts are left untouched."""
    with get_db() as conn:
        _get_campaign_row(conn, campaign_id)  # 404 if missing
        conn.execute("DELETE FROM promotion_campaigns WHERE id = ?", (campaign_id,))


def _resolve_campaign_targets(row) -> list[str]:
    """Resolve a campaign row's target definition to a capped list of IDs.

    Raises `product_service.BulkTargetLimitError` if the set exceeds the cap.
    """
    if row["target_type"] == "ids":
        product_ids = json.loads(row["target_ids"]) if row["target_ids"] else []
        return product_service.resolve_bulk_target(product_ids=product_ids)
    filt = json.loads(row["target_filter"]) if row["target_filter"] else {}
    return product_service.resolve_bulk_target(filter=filt)


def apply_campaign(campaign_id: str) -> dict:
    """Apply a campaign's discount to its resolved target products.

    Resolves targets at apply time, enforces the 500-product cap, writes the
    discount via the shared bulk logic, then records the resolved IDs and exact
    applied values for later conservative removal. Returns a bulk result dict.
    """
    with get_db() as conn:
        row = _get_campaign_row(conn, campaign_id)

    target_ids = _resolve_campaign_targets(row)
    result = product_service.bulk_update_discount(
        operation="apply",
        product_ids=target_ids,
        discount_percent=row["discount_percent"],
        discount_starts_at=row["discount_starts_at"],
        discount_ends_at=row["discount_ends_at"],
    )

    applied_at = pricing.now_utc()
    updated_ids = [r["id"] for r in result["results"] if r["status"] == "updated"]
    with get_db() as conn:
        # Replace prior applied-target records with this apply's successes.
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
        conn.execute(
            "UPDATE promotion_campaigns SET applied_at = ?, removed_at = NULL, updated_at = ? "
            "WHERE id = ?",
            (applied_at, applied_at, campaign_id),
        )

    logger.info(
        "campaign_applied",
        campaign_id=campaign_id,
        target_count=len(target_ids),
        success_count=result["success_count"],
        failure_count=result["failure_count"],
    )
    return result


def remove_campaign(campaign_id: str) -> dict:
    """Conservatively clear a campaign's discount from its applied products.

    Only products whose current discount fields still match the campaign's last
    applied values are cleared; edited products are skipped with a warning.
    """
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
    result = product_service.conservative_clear_discount(targets)

    removed_at = pricing.now_utc()
    with get_db() as conn:
        conn.execute(
            "UPDATE promotion_campaigns SET removed_at = ?, updated_at = ? WHERE id = ?",
            (removed_at, removed_at, campaign_id),
        )

    logger.info(
        "campaign_removed",
        campaign_id=campaign_id,
        target_count=len(targets),
        success_count=result["success_count"],
        failure_count=result["failure_count"],
    )
    return result
