"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { bulkDiscount } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { localInputToUtcIso } from "@/lib/datetime";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { BulkResultSummary } from "./BulkResultSummary";
import type { BulkDiscountResponse } from "@/lib/types";

interface ProductBulkDiscountBarProps {
  selectedIds: string[];
  onDone: () => void;
}

/**
 * Inline bulk action bar for the admin products list. Applies or clears a
 * discount on the current selection via the shared bulk discount endpoint and
 * shows the per-item "N updated, M failed" summary.
 */
export function ProductBulkDiscountBar({ selectedIds, onDone }: ProductBulkDiscountBarProps) {
  const t = useTranslations("admin");
  const getLocalizedError = useLocalizedError();

  const [mode, setMode] = useState<"apply" | "remove">("apply");
  const [percent, setPercent] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkDiscountResponse | null>(null);

  async function submit() {
    setError(null);
    if (mode === "apply") {
      const p = Number(percent);
      if (!percent || !Number.isInteger(p) || p < 1 || p > 99) {
        setError(t("promotions.percentRange"));
        return;
      }
      if (start && end && new Date(start) >= new Date(end)) {
        setError(t("promotions.windowInvalid"));
        return;
      }
    }
    setSubmitting(true);
    try {
      const res = await bulkDiscount({
        operation: mode,
        product_ids: selectedIds,
        discount_percent: mode === "apply" ? Number(percent) : null,
        discount_starts_at: mode === "apply" ? localInputToUtcIso(start) : null,
        discount_ends_at: mode === "apply" ? localInputToUtcIso(end) : null,
      });
      setResult(res);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("promotions.actionError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mb-4 rounded-brand border border-muted-gold/40 bg-muted-gold/5 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium text-charcoal">
          {t("promotions.selectedCount", { count: selectedIds.length })}
        </span>
        <div className="flex gap-2 text-sm">
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="bulk-mode"
              checked={mode === "apply"}
              onChange={() => setMode("apply")}
            />
            {t("promotions.applyDiscount")}
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="radio"
              name="bulk-mode"
              checked={mode === "remove"}
              onChange={() => setMode("remove")}
            />
            {t("promotions.clearDiscount")}
          </label>
        </div>
      </div>

      {mode === "apply" && (
        <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Input
            label={t("promotions.discountPercent")}
            type="number"
            min={1}
            max={99}
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
          />
          <div>
            <label htmlFor="bulk-start" className="mb-1.5 block text-sm font-medium text-soft-brown">
              {t("promotions.startsAt")}
            </label>
            <input
              id="bulk-start"
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
            />
          </div>
          <div>
            <label htmlFor="bulk-end" className="mb-1.5 block text-sm font-medium text-soft-brown">
              {t("promotions.endsAt")}
            </label>
            <input
              id="bulk-end"
              type="datetime-local"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
            />
          </div>
        </div>
      )}

      {error && <p className="mb-3 text-sm text-red-700">{error}</p>}

      <Button size="sm" onClick={submit} isLoading={submitting}>
        {mode === "apply" ? t("promotions.applyDiscount") : t("promotions.clearDiscount")}
      </Button>

      {result && (
        <div className="mt-3">
          <BulkResultSummary result={result} />
        </div>
      )}
    </div>
  );
}
