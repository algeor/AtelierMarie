"""Unit tests for the pricing helper (single source of truth for discounts)."""

import pytest

from app.services import pricing


class TestEffectivePriceCents:
    def test_twenty_percent_of_3250(self):
        assert pricing.effective_price_cents(3250, 20, active=True) == 2600

    def test_round_half_up_15_percent_of_999(self):
        # 999 * 0.85 = 849.15 → round-half-up → 849
        assert pricing.effective_price_cents(999, 15, active=True) == 849

    def test_round_half_up_boundary(self):
        # 101 * 0.50 = 50.5 → round-half-up → 51
        assert pricing.effective_price_cents(101, 50, active=True) == 51

    def test_floor_clamp_99_percent_of_1(self):
        # 1 * 0.01 = 0.01 → would round to 0 → clamped to 1
        assert pricing.effective_price_cents(1, 99, active=True) == 1

    def test_inactive_returns_list_price(self):
        assert pricing.effective_price_cents(3250, 20, active=False) == 3250

    def test_none_percent_returns_list_price(self):
        assert pricing.effective_price_cents(3250, None, active=True) == 3250


class TestDiscountIsActive:
    def test_manual_discount_no_dates_active(self):
        assert pricing.discount_is_active(20, None, None, "2026-07-25 12:00:00") is True

    def test_none_percent_never_active(self):
        assert pricing.discount_is_active(None, None, None, "2026-07-25 12:00:00") is False

    def test_before_window(self):
        assert (
            pricing.discount_is_active(20, "2026-08-01 00:00:00", None, "2026-07-25 12:00:00")
            is False
        )

    def test_after_window(self):
        assert (
            pricing.discount_is_active(20, None, "2026-07-01 00:00:00", "2026-07-25 12:00:00")
            is False
        )

    def test_within_window(self):
        assert (
            pricing.discount_is_active(
                20, "2026-07-01 00:00:00", "2026-08-01 00:00:00", "2026-07-25 12:00:00"
            )
            is True
        )

    def test_inclusive_start_boundary(self):
        assert (
            pricing.discount_is_active(20, "2026-07-25 12:00:00", None, "2026-07-25 12:00:00")
            is True
        )

    def test_inclusive_end_boundary(self):
        assert (
            pricing.discount_is_active(20, None, "2026-07-25 12:00:00", "2026-07-25 12:00:00")
            is True
        )


class TestNormalizeDiscountDatetime:
    def test_none_passthrough(self):
        assert pricing.normalize_discount_datetime(None) is None

    def test_empty_string_becomes_none(self):
        assert pricing.normalize_discount_datetime("   ") is None

    def test_canonical_utc_preserved(self):
        assert pricing.normalize_discount_datetime("2026-08-01 09:30:00") == "2026-08-01 09:30:00"

    def test_timezone_aware_iso_converted_to_utc(self):
        # +03:00 offset → subtract 3h to reach UTC
        assert (
            pricing.normalize_discount_datetime("2026-08-01T12:30:00+03:00")
            == "2026-08-01 09:30:00"
        )

    def test_trailing_z_treated_as_utc(self):
        assert pricing.normalize_discount_datetime("2026-08-01T09:30:00Z") == "2026-08-01 09:30:00"

    def test_timezone_less_iso_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            pricing.normalize_discount_datetime("2026-08-01T12:30:00")

    def test_garbage_rejected(self):
        with pytest.raises(ValueError, match="invalid discount datetime"):
            pricing.normalize_discount_datetime("not-a-date")


class TestAnnotateProductPricing:
    def _product(self, **overrides):
        base = {
            "id": "x",
            "price_cents": 3250,
            "discount_percent": 20,
            "discount_starts_at": None,
            "discount_ends_at": None,
        }
        base.update(overrides)
        return base

    def test_public_active_exposes_percent_and_hides_window(self):
        result = pricing.annotate_product_pricing(
            self._product(discount_starts_at="2026-01-01 00:00:00"),
            now="2026-07-25 12:00:00",
            public=True,
        )
        assert result["discount_active"] is True
        assert result["effective_price_cents"] == 2600
        assert result["discount_percent"] == 20
        assert "discount_starts_at" not in result
        assert "discount_ends_at" not in result

    def test_public_inactive_nulls_percent_and_reverts_price(self):
        result = pricing.annotate_product_pricing(
            self._product(discount_starts_at="2099-01-01 00:00:00"),
            now="2026-07-25 12:00:00",
            public=True,
        )
        assert result["discount_active"] is False
        assert result["discount_percent"] is None
        assert result["effective_price_cents"] == 3250

    def test_admin_keeps_raw_fields_and_adds_preview(self):
        result = pricing.annotate_product_pricing(
            self._product(
                discount_starts_at="2099-01-01 00:00:00",
                discount_ends_at="2099-02-01 00:00:00",
            ),
            now="2026-07-25 12:00:00",
            public=False,
        )
        # Inactive future schedule, but admin still sees the raw config.
        assert result["discount_active"] is False
        assert result["discount_percent"] == 20
        assert result["discount_starts_at"] == "2099-01-01 00:00:00"
        assert result["discount_ends_at"] == "2099-02-01 00:00:00"
        assert result["effective_price_cents"] == 3250
