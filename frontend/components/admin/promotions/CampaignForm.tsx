"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { createCampaign, getAdminProducts, updateCampaign } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { localInputToUtcIso, storedUtcToLocalInput } from "@/lib/datetime";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type {
  AdminProductResponse,
  CampaignCreateRequest,
  CampaignResponse,
  CampaignUpdateRequest,
  ProductFilter,
} from "@/lib/types";

type TargetMode = "ids" | "filter";

interface CampaignFormProps {
  campaign: CampaignResponse | null;
  onSaved: () => void;
  onCancel: () => void;
}

export function CampaignForm({ campaign, onSaved, onCancel }: CampaignFormProps) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();
  const isEdit = campaign !== null;

  const [name, setName] = useState(campaign?.name ?? "");
  const [note, setNote] = useState(campaign?.note ?? "");
  const [percent, setPercent] = useState<string>(
    campaign ? String(campaign.discount_percent) : ""
  );
  const [start, setStart] = useState(storedUtcToLocalInput(campaign?.discount_starts_at ?? null));
  const [end, setEnd] = useState(storedUtcToLocalInput(campaign?.discount_ends_at ?? null));
  const [targetMode, setTargetMode] = useState<TargetMode>(campaign?.target_type ?? "ids");

  // Explicit-IDs target: a client-side selected-ID set that survives paging.
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [products, setProducts] = useState<AdminProductResponse[]>([]);
  const [productSearch, setProductSearch] = useState("");

  // Filter target descriptor.
  const [filterQ, setFilterQ] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterActive, setFilterActive] = useState<"all" | "active" | "inactive">("all");
  const [filterInStock, setFilterInStock] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadProducts = useCallback(async () => {
    try {
      const data = await getAdminProducts(1, 100);
      setProducts(data.products);
    } catch {
      // Non-fatal: the explicit picker just shows no rows.
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  function toggleId(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function buildFilter(): ProductFilter {
    const filter: ProductFilter = {};
    if (filterQ.trim()) filter.q = filterQ.trim();
    if (filterCategory.trim()) filter.category = filterCategory.trim();
    if (filterActive !== "all") filter.is_active = filterActive === "active";
    if (filterInStock) filter.in_stock = true;
    return filter;
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = t("promotions.nameRequired");
    const p = Number(percent);
    if (!percent || !Number.isInteger(p) || p < 1 || p > 99) {
      next.percent = t("promotions.percentRange");
    }
    if (start && end && new Date(start) >= new Date(end)) {
      next.window = t("promotions.windowInvalid");
    }
    if (targetMode === "ids" && selectedIds.size === 0) {
      next.target = t("promotions.targetRequired");
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!validate()) return;

    const discountFields = {
      discount_percent: Number(percent),
      discount_starts_at: localInputToUtcIso(start),
      discount_ends_at: localInputToUtcIso(end),
    };
    const target =
      targetMode === "ids"
        ? { product_ids: Array.from(selectedIds), filter: null }
        : { product_ids: null, filter: buildFilter() };

    setSubmitting(true);
    try {
      if (isEdit) {
        const payload: CampaignUpdateRequest = {
          name: name.trim(),
          note: note.trim() || null,
          ...discountFields,
          ...target,
        };
        await updateCampaign(campaign.id, payload);
      } else {
        const payload: CampaignCreateRequest = {
          name: name.trim(),
          note: note.trim() || null,
          ...discountFields,
          ...target,
        };
        await createCampaign(payload);
      }
      onSaved();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? getLocalizedError(err.code) : t("promotions.saveError")
      );
    } finally {
      setSubmitting(false);
    }
  }

  const visibleProducts = products.filter((p) => {
    if (!productSearch.trim()) return true;
    const q = productSearch.toLowerCase();
    return p.name_en.toLowerCase().includes(q) || p.id.toLowerCase().includes(q);
  });

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {formError && (
        <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {formError}
        </div>
      )}

      <Input
        label={t("promotions.campaignName")}
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={errors.name}
        maxLength={200}
      />

      <div>
        <label htmlFor="campaign-note" className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t("promotions.note")} <span className="text-soft-brown/60">({t("optional")})</span>
        </label>
        <textarea
          id="campaign-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={2000}
          rows={2}
          className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
        />
      </div>

      <Input
        label={t("promotions.discountPercent")}
        type="number"
        min={1}
        max={99}
        value={percent}
        onChange={(e) => setPercent(e.target.value)}
        error={errors.percent}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="campaign-start" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("promotions.startsAt")} <span className="text-soft-brown/60">({t("optional")})</span>
          </label>
          <input
            id="campaign-start"
            type="datetime-local"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
          />
        </div>
        <div>
          <label htmlFor="campaign-end" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("promotions.endsAt")} <span className="text-soft-brown/60">({t("optional")})</span>
          </label>
          <input
            id="campaign-end"
            type="datetime-local"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
          />
        </div>
      </div>
      {errors.window && <p className="text-sm text-red-700">{errors.window}</p>}

      {/* Target selection */}
      <fieldset className="rounded-brand border border-champagne-beige p-4">
        <legend className="px-1 text-sm font-medium text-charcoal">
          {t("promotions.targets")}
        </legend>
        <div className="mb-3 flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="target-mode"
              checked={targetMode === "ids"}
              onChange={() => setTargetMode("ids")}
            />
            {t("promotions.targetExplicit")}
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="target-mode"
              checked={targetMode === "filter"}
              onChange={() => setTargetMode("filter")}
            />
            {t("promotions.targetFilter")}
          </label>
        </div>

        {targetMode === "ids" ? (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <Input
                placeholder={t("promotions.searchProducts")}
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                className="max-w-xs"
              />
              <span className="text-sm text-soft-brown">
                {t("promotions.selectedCount", { count: selectedIds.size })}
              </span>
            </div>
            <div className="max-h-56 overflow-y-auto rounded-brand border border-champagne-beige">
              {visibleProducts.map((p) => (
                <label
                  key={p.id}
                  className="flex cursor-pointer items-center gap-2 border-b border-champagne-beige/50 px-3 py-2 text-sm last:border-0 hover:bg-champagne-beige/20"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(p.id)}
                    onChange={() => toggleId(p.id)}
                  />
                  <span className="flex-1 text-charcoal">{p.name_en}</span>
                  <code className="text-xs text-soft-brown">{p.id}</code>
                </label>
              ))}
              {visibleProducts.length === 0 && (
                <p className="px-3 py-4 text-center text-sm text-soft-brown">
                  {t("noProducts")}
                </p>
              )}
            </div>
            {errors.target && <p className="mt-1 text-sm text-red-700">{errors.target}</p>}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Input
              label={t("promotions.filterSearch")}
              value={filterQ}
              onChange={(e) => setFilterQ(e.target.value)}
            />
            <Input
              label={t("category")}
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            />
            <div>
              <label htmlFor="filter-active" className="mb-1.5 block text-sm font-medium text-soft-brown">
                {t("status")}
              </label>
              <select
                id="filter-active"
                value={filterActive}
                onChange={(e) => setFilterActive(e.target.value as typeof filterActive)}
                className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
              >
                <option value="all">{t("all")}</option>
                <option value="active">{t("active")}</option>
                <option value="inactive">{t("inactive")}</option>
              </select>
            </div>
            <label className="flex items-center gap-2 pt-8 text-sm text-soft-brown">
              <input
                type="checkbox"
                checked={filterInStock}
                onChange={(e) => setFilterInStock(e.target.checked)}
              />
              {t("promotions.inStockOnly")}
            </label>
            <p className="col-span-full text-xs text-soft-brown/70">
              {t("promotions.filterCountNote")}
            </p>
          </div>
        )}
      </fieldset>

      <p className="text-xs text-soft-brown/70">{t("promotions.bannerHelper")}</p>

      <div className="flex gap-3">
        <Button type="submit" isLoading={submitting}>
          {isEdit ? tCommon("save") : t("promotions.createCampaign")}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          {tCommon("cancel")}
        </Button>
      </div>
    </form>
  );
}
