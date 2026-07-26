"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  applyCampaign,
  deleteCampaign,
  getCampaigns,
  removeCampaign,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { CampaignForm } from "./CampaignForm";
import { BulkResultSummary } from "./BulkResultSummary";
import type { BulkDiscountResponse, CampaignResponse, CampaignStatus } from "@/lib/types";

type StatusVariant = "default" | "accent" | "success" | "warning";
const STATUS_VARIANT: Record<CampaignStatus, StatusVariant> = {
  draft: "default",
  scheduled: "accent",
  active: "success",
  ended: "warning",
  removed: "default",
};

type PendingAction =
  | { type: "apply" | "remove" | "delete"; campaign: CampaignResponse }
  | null;

export function CampaignsPanel() {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();

  const [campaigns, setCampaigns] = useState<CampaignResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<CampaignResponse | null>(null);
  const [pending, setPending] = useState<PendingAction>(null);
  const [actioning, setActioning] = useState(false);
  const [lastResult, setLastResult] = useState<BulkDiscountResponse | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCampaigns();
      setCampaigns(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("promotions.loadError"));
    } finally {
      setLoading(false);
    }
  }, [getLocalizedError, t]);

  useEffect(() => {
    load();
  }, [load]);

  // Close the confirmation dialog on Escape.
  useEffect(() => {
    if (!pending) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !actioning) setPending(null);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [pending, actioning]);

  function statusLabel(status: CampaignStatus): string {
    return t(`promotions.status.${status}`);
  }

  function discountSummary(c: CampaignResponse): string {
    return t("promotions.percentOff", { percent: c.discount_percent });
  }

  async function confirmAction() {
    if (!pending) return;
    setActioning(true);
    setError(null);
    try {
      if (pending.type === "delete") {
        await deleteCampaign(pending.campaign.id);
        setLastResult(null);
      } else {
        const result =
          pending.type === "apply"
            ? await applyCampaign(pending.campaign.id)
            : await removeCampaign(pending.campaign.id);
        setLastResult(result);
      }
      setPending(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("promotions.actionError"));
    } finally {
      setActioning(false);
    }
  }

  if (showForm) {
    return (
      <div className="rounded-brand border border-champagne-beige bg-cream p-6">
        <h2 className="mb-4 font-heading text-lg font-semibold text-charcoal">
          {editing ? t("promotions.editCampaign") : t("promotions.newCampaign")}
        </h2>
        <CampaignForm
          campaign={editing}
          onSaved={() => {
            setShowForm(false);
            setEditing(null);
            load();
          }}
          onCancel={() => {
            setShowForm(false);
            setEditing(null);
          }}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-heading text-lg font-semibold text-charcoal">
          {t("promotions.campaigns")}
        </h2>
        <Button
          onClick={() => {
            setEditing(null);
            setShowForm(true);
          }}
        >
          {t("promotions.createCampaign")}
        </Button>
      </div>

      {error && (
        <div className="mb-4 rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {lastResult && (
        <div className="mb-4">
          <BulkResultSummary result={lastResult} />
        </div>
      )}

      {loading ? (
        <p className="text-sm text-soft-brown">{tCommon("loading")}</p>
      ) : campaigns.length === 0 ? (
        <p className="rounded-brand border border-champagne-beige bg-cream px-4 py-8 text-center text-sm text-soft-brown">
          {t("promotions.noCampaigns")}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-champagne-beige bg-champagne-beige/30">
                <th className="px-4 py-3 font-medium text-charcoal">{t("promotions.campaignName")}</th>
                <th className="px-4 py-3 font-medium text-charcoal">{t("status")}</th>
                <th className="px-4 py-3 font-medium text-charcoal">{t("promotions.discount")}</th>
                <th className="px-4 py-3 font-medium text-charcoal">{t("promotions.targetCount")}</th>
                <th className="px-4 py-3 font-medium text-charcoal">{t("actions")}</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} className="border-b border-champagne-beige/50 last:border-0">
                  <td className="px-4 py-3 font-medium text-charcoal">{c.name}</td>
                  <td className="px-4 py-3">
                    <Badge variant={STATUS_VARIANT[c.status]}>{statusLabel(c.status)}</Badge>
                  </td>
                  <td className="px-4 py-3 text-soft-brown">{discountSummary(c)}</td>
                  <td className="px-4 py-3 text-soft-brown">{c.target_count}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => {
                          setEditing(c);
                          setShowForm(true);
                        }}
                        className="inline-flex h-8 items-center rounded-brand px-3 text-xs font-medium text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal"
                      >
                        {tCommon("edit")}
                      </button>
                      <Button
                        size="sm"
                        onClick={() => setPending({ type: "apply", campaign: c })}
                      >
                        {t("promotions.apply")}
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setPending({ type: "remove", campaign: c })}
                      >
                        {t("promotions.removeDiscount")}
                      </Button>
                      <button
                        onClick={() => setPending({ type: "delete", campaign: c })}
                        className="inline-flex h-8 items-center rounded-brand px-3 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        {tCommon("delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Apply / Remove / Delete confirmation */}
      {pending && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/40 p-4"
          onClick={() => !actioning && setPending(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="campaign-confirm-title"
            className="w-full max-w-md rounded-brand border border-champagne-beige bg-cream p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3
              id="campaign-confirm-title"
              className="mb-3 font-heading text-lg font-semibold text-charcoal"
            >
              {pending.type === "apply"
                ? t("promotions.confirmApplyTitle")
                : pending.type === "remove"
                  ? t("promotions.confirmRemoveTitle")
                  : t("promotions.confirmDeleteTitle")}
            </h3>
            <p className="mb-4 text-sm text-soft-brown">
              {pending.type === "apply"
                ? t("promotions.confirmApplyBody", {
                    percent: pending.campaign.discount_percent,
                    count: pending.campaign.target_count,
                  })
                : pending.type === "remove"
                  ? t("promotions.confirmRemoveBody")
                  : t("promotions.confirmDelete", { name: pending.campaign.name })}
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => setPending(null)}
                disabled={actioning}
                autoFocus
              >
                {tCommon("cancel")}
              </Button>
              <Button onClick={confirmAction} isLoading={actioning}>
                {pending.type === "apply"
                  ? t("promotions.apply")
                  : pending.type === "remove"
                    ? t("promotions.removeDiscount")
                    : tCommon("delete")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
