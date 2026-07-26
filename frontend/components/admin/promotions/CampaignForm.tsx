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
const PRODUCT_PAGE_LIMIT = 100;

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
  // Pre-seed from the campaign so editing metadata doesn't wipe the target.
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(campaign?.target_ids ?? [])
  );
  const [products, setProducts] = useState<AdminProductResponse[]>([]);
  const [productPage, setProductPage] = useState(1);
  const [productTotal, setProductTotal] = useState(0);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productSearch, setProductSearch] = useState("");

  // Filter target descriptor (pre-seeded from the campaign's stored filter).
  const [filterQ, setFilterQ] = useState(campaign?.target_filter?.q ?? "");
  const [filterCategory, setFilterCategory] = useState(campaign?.target_filter?.category ?? "");
  const [filterActive, setFilterActive] = useState<"all" | "active" | "inactive">(
    campaign?.target_filter?.is_active == null
      ? "all"
      : campaign.target_filter.is_active
        ? "active"
        : "inactive"
  );
  const [filterInStock, setFilterInStock] = useState(campaign?.target_filter?.in_stock ?? false);
  const [targetDirty, setTargetDirty] = useState(false);
  // Discount fields are only sent on edit when actually changed, so a metadata
  // edit of a live campaign doesn't trip the backend's discount-edit guard.
  const [discountDirty, setDiscountDirty] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadProducts = useCallback(async (page: number) => {
    setProductsLoading(true);
    try {
      const data = await getAdminProducts(page, PRODUCT_PAGE_LIMIT);
      setProducts(data.products);
      setProductPage(data.page);
      setProductTotal(data.total);
    } catch {
      // Non-fatal: the explicit picker just shows no rows.
      setProducts([]);
      setProductTotal(0);
    } finally {
      setProductsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (targetMode === "ids") loadProducts(productPage);
  }, [loadProducts, productPage, targetMode]);

  function toggleId(id: string) {
    setTargetDirty(true);
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

  function buildTarget(): Pick<CampaignCreateRequest, "product_ids" | "filter"> {
    return targetMode === "ids"
      ? { product_ids: Array.from(selectedIds), filter: null }
      : { product_ids: null, filter: buildFilter() };
  }

  function handleTargetModeChange(mode: TargetMode) {
    if (mode !== targetMode) setTargetDirty(true);
    setTargetMode(mode);
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
    if ((!isEdit || targetDirty) && targetMode === "ids" && selectedIds.size === 0) {
      next.target = t("promotions.targetRequired");
    }
    if (
      (!isEdit || targetDirty) &&
      targetMode === "filter" &&
      Object.keys(buildFilter()).length === 0
    ) {
      next.target = t("promotions.filterRequired");
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
    const target = buildTarget();

    setSubmitting(true);
    try {
      if (isEdit) {
        const payload: CampaignUpdateRequest = {
          name: name.trim(),
          note: note.trim() || null,
          ...(discountDirty ? discountFields : {}),
          ...(targetDirty ? target : {}),
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
  const productPageCount = Math.max(1, Math.ceil(productTotal / PRODUCT_PAGE_LIMIT));

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
        onChange={(e) => {
          setDiscountDirty(true);
          setPercent(e.target.value);
        }}
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
            onChange={(e) => {
              setDiscountDirty(true);
              setStart(e.target.value);
            }}
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
            onChange={(e) => {
              setDiscountDirty(true);
              setEnd(e.target.value);
            }}
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
              onChange={() => handleTargetModeChange("ids")}
            />
            {t("promotions.targetExplicit")}
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="target-mode"
              checked={targetMode === "filter"}
              onChange={() => handleTargetModeChange("filter")}
            />
            {t("promotions.targetFilter")}
          </label>
        </div>

        {targetMode === "ids" ? (
          <div>
            <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <Input
                placeholder={t("promotions.searchProducts")}
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                className="max-w-xs"
              />
              <div className="flex flex-wrap items-center gap-3 text-sm text-soft-brown">
                <span>{t("promotions.selectedCount", { count: selectedIds.size })}</span>
                <span>{tCommon("page", { current: productPage, total: productPageCount })}</span>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => setProductPage((page) => Math.max(1, page - 1))}
                    disabled={productsLoading || productPage <= 1}
                  >
                    {tCommon("previous")}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => setProductPage((page) => Math.min(productPageCount, page + 1))}
                    disabled={productsLoading || productPage >= productPageCount}
                  >
                    {tCommon("next")}
                  </Button>
                </div>
              </div>
            </div>
            <div className="max-h-56 overflow-y-auto rounded-brand border border-champagne-beige">
              {productsLoading ? (
                <p className="px-3 py-4 text-center text-sm text-soft-brown">
                  {tCommon("loading")}
                </p>
              ) : (
                visibleProducts.map((p) => (
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
                ))
              )}
              {!productsLoading && visibleProducts.length === 0 && (
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
              onChange={(e) => {
                setTargetDirty(true);
                setFilterQ(e.target.value);
              }}
            />
            <Input
              label={t("category")}
              value={filterCategory}
              onChange={(e) => {
                setTargetDirty(true);
                setFilterCategory(e.target.value);
              }}
            />
            <div>
              <label htmlFor="filter-active" className="mb-1.5 block text-sm font-medium text-soft-brown">
                {t("status")}
              </label>
              <select
                id="filter-active"
                value={filterActive}
                onChange={(e) => {
                  setTargetDirty(true);
                  setFilterActive(e.target.value as typeof filterActive);
                }}
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
                onChange={(e) => {
                  setTargetDirty(true);
                  setFilterInStock(e.target.checked);
                }}
              />
              {t("promotions.inStockOnly")}
            </label>
            <p className="col-span-full text-xs text-soft-brown/70">
              {t("promotions.filterCountNote")}
            </p>
            {errors.target && (
              <p className="col-span-full text-sm text-red-700">{errors.target}</p>
            )}
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
