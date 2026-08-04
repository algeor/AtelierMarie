"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getAdminProducts, updateProduct } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { ProductBulkDiscountBar } from "@/components/admin/promotions/ProductBulkDiscountBar";
import type { AdminProductResponse } from "@/lib/types";

export default function AdminProductsPage() {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();
  const searchParams = useSearchParams();
  const [products, setProducts] = useState<AdminProductResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [successNoticeId, setSuccessNoticeId] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const selectAllRef = useRef<HTMLInputElement>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Show success banner from query param
  useEffect(() => {
    const success = searchParams.get("success");
    const messages: Record<string, string> = {
      created: t("productCreated"),
      updated: t("productUpdated"),
    };
    if (success && messages[success]) {
      showSuccess(messages[success]);
      // Strip param from URL to prevent re-flash on refresh
      window.history.replaceState({}, "", window.location.pathname);
    }
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, [searchParams, t]);

  const loadProducts = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getAdminProducts(1, 100);
      setProducts(data.products);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.loadProducts"));
    } finally {
      setIsLoading(false);
    }
  }, [getLocalizedError, t]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  async function toggleActive(product: AdminProductResponse) {
    const previousActive = product.is_active;
    setTogglingId(product.id);

    // Optimistic update
    setProducts((prev) =>
      prev.map((p) =>
        p.id === product.id ? { ...p, is_active: !p.is_active } : p
      )
    );

    try {
      const updated = await updateProduct(product.id, {
        is_active: !previousActive,
      });
      setProducts((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p))
      );
      showSuccess(tCommon("saved"));
    } catch (err) {
      // Rollback
      setProducts((prev) =>
        prev.map((p) =>
          p.id === product.id ? { ...p, is_active: previousActive } : p
        )
      );
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.updateProduct"));
    } finally {
      setTogglingId(null);
    }
  }

  function showSuccess(message: string) {
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
    setSuccessMessage(message);
    setSuccessNoticeId((current) => current + 1);
    successTimerRef.current = setTimeout(() => {
      setSuccessMessage(null);
    }, 3200);
  }

  function dismissSuccess() {
    setSuccessMessage(null);
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
  }

  function toggleSelected(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) =>
      prev.size === products.length ? new Set() : new Set(products.map((p) => p.id))
    );
  }

  const allSelected = products.length > 0 && selectedIds.size === products.length;

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = selectedIds.size > 0 && !allSelected;
    }
  }, [selectedIds, allSelected]);

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-heading text-2xl font-semibold text-charcoal">
              {t("products")}
            </h1>
          </div>
        </div>
        <Link
          href="/admin/products/new"
          className="inline-flex h-10 items-center justify-center rounded-brand bg-charcoal px-4 text-sm font-medium text-cream transition-colors hover:bg-charcoal/90"
        >
          {t("createProduct")}
        </Link>
      </div>

      {successMessage && (
        <SaveConfirmation
          key={successNoticeId}
          message={successMessage}
          onDismiss={dismissSuccess}
          dismissLabel={t("dismissSuccess")}
        />
      )}

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {selectedIds.size > 0 && (
        <ProductBulkDiscountBar
          selectedIds={Array.from(selectedIds)}
          onDone={() => {
            loadProducts();
          }}
        />
      )}

      <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-champagne-beige bg-champagne-beige/30">
              <th className="px-4 py-3">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  aria-label={t("promotions.selectAll")}
                />
              </th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("name")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("category")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("price")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("stock")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("inventoryColumn")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("status")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("actions")}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-champagne-beige/50">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-4" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-10" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-28" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-8 w-24" /></td>
                </tr>
              ))
            ) : products.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-soft-brown">
                  {t("noProducts")}
                </td>
              </tr>
            ) : (
              products.map((product) => (
                <tr
                  key={product.id}
                  className="border-b border-champagne-beige/50 last:border-0"
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(product.id)}
                      onChange={() => toggleSelected(product.id)}
                      aria-label={product.name_en}
                    />
                  </td>
                  <td className="px-4 py-3 font-medium text-charcoal">
                    {product.name_en}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {product.category || "—"}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {formatPrice(product.price_cents)}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">{product.stock}</td>
                  <td className="px-4 py-3 text-xs text-soft-brown">
                    <div className="flex flex-col gap-1">
                      <span className="inline-flex w-fit rounded-pill bg-champagne-beige/60 px-2 py-0.5 font-medium capitalize text-soft-brown">
                        {(product.inventory_mode ?? "legacy").replaceAll("_", " ")}
                      </span>
                      <span>{t("recipeStatus")}: {product.active_recipe_status ?? "missing"}</span>
                      <span>{t("stockSource")}: {(product.stock_source ?? "product_stock").replaceAll("_", " ")}</span>
                      {product.latest_batch_number && (
                        <Link href={`/admin/inventory/batches?product_id=${product.id}`} className="font-medium text-charcoal underline-offset-2 hover:underline">
                          {product.latest_batch_number}
                        </Link>
                      )}
                      {Boolean(product.inventory_exception_count) && (
                        <Link href={`/admin/inventory/valuation/exceptions?target_type=product&target_id=${product.id}`} className="font-medium text-amber-800 underline-offset-2 hover:underline">
                          {t("inventoryExceptions", { count: product.inventory_exception_count ?? 0 })}
                        </Link>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={product.is_active ? "success" : "warning"}>
                      {product.is_active ? t("active") : t("inactive")}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/products/${product.id}/edit`}
                        className="inline-flex h-8 items-center justify-center rounded-brand px-3 text-xs font-medium text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal"
                      >
                        {tCommon("edit")}
                      </Link>
                      <Button
                        variant="secondary"
                        size="sm"
                        isLoading={togglingId === product.id}
                        onClick={() => toggleActive(product)}
                      >
                        {product.is_active ? t("deactivate") : t("activate")}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* CSV Import Format Reference */}
      <details className="mt-8 rounded-brand border border-champagne-beige bg-cream">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/30">
          {t("csvReference")}
        </summary>
        <div className="border-t border-champagne-beige px-4 py-4 text-sm text-soft-brown">
          <p className="mb-3">
            {t("csvImportDescription", { endpoint: "POST /v1/admin/products/import" })}
          </p>
          <p className="mb-2 font-medium text-charcoal">{t("requiredColumns")}</p>
          <ul className="mb-3 ml-4 list-disc space-y-1">
            <li><code className="text-xs">id</code> - {t("csvColumnId")} (<code className="text-xs">lavender-dreams-300ml</code>)</li>
            <li><code className="text-xs">name_en</code> - {t("csvColumnNameEn")}</li>
            <li><code className="text-xs">price_cents</code> - {t("csvColumnPrice")}</li>
            <li><code className="text-xs">category</code> - {t("csvColumnCategory")}</li>
            <li><code className="text-xs">stock</code> - {t("csvColumnStock")}</li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">{t("optionalBilingualColumns")}</p>
          <ul className="mb-3 ml-4 list-disc space-y-1">
            <li><code className="text-xs">name_bg</code> - {t("csvColumnNameBg")}</li>
            <li><code className="text-xs">description_en</code> - {t("csvColumnDescriptionEn")}</li>
            <li><code className="text-xs">description_bg</code> - {t("csvColumnDescriptionBg")}</li>
            <li><code className="text-xs">materials</code>, <code className="text-xs">days_to_craft</code>, <code className="text-xs">image_url</code>, <code className="text-xs">is_featured</code>, <code className="text-xs">is_active</code>, <code className="text-xs">weight_grams</code></li>
            <li><code className="text-xs">safety_warnings_en</code>, <code className="text-xs">safety_warnings_bg</code>, <code className="text-xs">care_instructions_en</code>, <code className="text-xs">care_instructions_bg</code></li>
          </ul>
          <p className="mb-2 font-medium text-charcoal">{t("example")}</p>
          <pre className="overflow-x-auto rounded bg-charcoal/5 p-3 text-xs leading-relaxed">
{`id,name_en,name_bg,description_en,description_bg,price_cents,category,stock,weight_grams,is_active,safety_warnings_en,care_instructions_en
lavender-dreams-300ml,Lavender Dreams,Лавандулов сън,Hand-poured soy candle,Ръчно излята соева свещ,3200,Floral,24,300,true,Never leave unattended.,Trim wick before use.
midnight-amber-300ml,Midnight Amber,Полунощен кехлибар,Warm amber and sandalwood,Топъл кехлибар и сандалово дърво,4500,Woody,12,450,true,Never leave unattended.,Use on a heat-resistant surface.`}
          </pre>
          <p className="mt-3 text-xs text-soft-brown/70">
            {t("csvFallbackNote")}
          </p>
        </div>
      </details>
    </div>
  );
}
