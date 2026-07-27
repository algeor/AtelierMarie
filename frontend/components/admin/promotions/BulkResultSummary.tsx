"use client";

import { useTranslations } from "next-intl";
import type { BulkDiscountResponse } from "@/lib/types";

/**
 * Renders a per-item bulk/campaign result summary: "N updated, M failed"
 * plus an expandable list of skipped/failed products with their messages.
 * Shared by the campaign apply/remove flows and the products-list bulk bar.
 */
export function BulkResultSummary({ result }: { result: BulkDiscountResponse }) {
  const t = useTranslations("admin");
  const skippedOrFailed = result.results.filter((r) => r.status !== "updated");

  return (
    <div className="rounded-brand border border-champagne-beige bg-cream p-4 text-sm">
      <p className="font-medium text-charcoal">
        {t("promotions.resultSummary", {
          updated: result.success_count,
          failed: result.failure_count,
        })}
      </p>
      {skippedOrFailed.length > 0 && (
        <ul className="mt-2 space-y-1 text-soft-brown">
          {skippedOrFailed.map((r) => (
            <li key={r.id} className="flex gap-2">
              <span
                className={
                  r.status === "failed" ? "font-medium text-red-700" : "font-medium text-amber-700"
                }
              >
                {r.status === "failed" ? t("promotions.failed") : t("promotions.skipped")}
              </span>
              <code className="text-xs">{r.id}</code>
              {r.error && <span className="text-xs text-soft-brown/80">— {r.error}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
