"use client";

import { useEffect, useState, type FormEvent } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError, BASE_URL } from "@/lib/api-client";
import { getAdminTaxonomy } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AdminProductResponse, AdminTaxonomyTerm, ProductImage } from "@/lib/types";
import { useLocalizedError } from "@/lib/useLocalizedError";

interface ProductFormProps {
  product?: AdminProductResponse;
  onSubmit: (data: ProductFormData) => Promise<void>;
  submitLabel: string;
}

export interface ProductFormData {
  id: string;
  name_en: string;
  name_bg: string;
  description_en: string;
  description_bg: string;
  materials: string;
  days_to_craft: number | null;
  price_cents: number;
  product_type: string;
  category: string;
  labels: string[];
  image_files: File[];
  ordered_image_ids: string[];
  deleted_image_ids: string[];
  primary_image_id: string | null;
  stock: number;
  is_featured: boolean;
}

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;

/** Convert a EUR string (e.g., "32.50") to cents without floating-point errors. */
function eurToCents(value: string): number {
  const trimmed = value.trim();
  if (!trimmed) return 0;
  const parts = trimmed.split(".");
  const whole = parseInt(parts[0] || "0", 10);
  const fracStr = (parts[1] || "").padEnd(2, "0").slice(0, 2);
  const frac = parseInt(fracStr, 10);
  if (isNaN(whole) || isNaN(frac)) return 0;
  return whole * 100 + (whole < 0 ? -frac : frac);
}

export function ProductForm({ product, onSubmit, submitLabel }: ProductFormProps) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [images, setImages] = useState<ProductImage[]>(product?.images ?? []);
  const [deletedImageIds, setDeletedImageIds] = useState<string[]>([]);

  // Local string state for price input to avoid cursor jumping
  const [priceDisplay, setPriceDisplay] = useState(
    product?.price_cents ? (product.price_cents / 100).toFixed(2) : ""
  );

  const [formData, setFormData] = useState<ProductFormData>({
    id: product?.id ?? "",
    name_en: product?.name_en ?? "",
    name_bg: product?.name_bg ?? "",
    description_en: product?.description_en ?? "",
    description_bg: product?.description_bg ?? "",
    materials: product?.materials ?? "",
    days_to_craft: product?.days_to_craft ?? null,
    price_cents: product?.price_cents ?? 0,
    product_type: product?.product_type ?? "",
    category: product?.category ?? "",
    labels: product?.labels ?? [],
    image_files: [],
    ordered_image_ids: (product?.images ?? []).map((image) => image.id),
    deleted_image_ids: [],
    primary_image_id: product?.images.find((image) => image.is_primary)?.id ?? null,
    stock: product?.stock ?? 0,
    is_featured: product?.is_featured ?? false,
  });

  // Managed taxonomy, fetched from the API (no hardcoded lists).
  const [productTypes, setProductTypes] = useState<AdminTaxonomyTerm[]>([]);
  const [categories, setCategories] = useState<AdminTaxonomyTerm[]>([]);
  const [labelTerms, setLabelTerms] = useState<AdminTaxonomyTerm[]>([]);

  useEffect(() => {
    Promise.all([
      getAdminTaxonomy("product-types"),
      getAdminTaxonomy("categories"),
      getAdminTaxonomy("labels"),
    ])
      .then(([types, cats, labels]) => {
        setProductTypes(types);
        setCategories(cats);
        setLabelTerms(labels);
      })
      .catch(() => setError(t("taxonomy.loadError")));
    // Load taxonomy once on mount; `t` is read only for the error message and
    // must not re-trigger the fetch if its identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Options for a single-select: active terms, plus the product's current term
   * even if it has been retired (so edits preserve it). Other inactive terms
   * are not assignable.
   */
  function selectOptions(terms: AdminTaxonomyTerm[], current: string) {
    const options = terms.filter((term) => term.is_active);
    const currentTerm = terms.find((term) => term.slug === current);
    if (currentTerm && !currentTerm.is_active) options.push(currentTerm);
    return options;
  }

  // Labels: active labels plus any currently-assigned retired labels.
  const labelOptions = [
    ...labelTerms.filter((term) => term.is_active),
    ...labelTerms.filter((term) => !term.is_active && formData.labels.includes(term.slug)),
  ];

  const translationStaleBg = product?.translation_stale_bg;
  const translationStaleEn = product?.translation_stale_en;

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!formData.name_en.trim()) newErrors.name_en = t("validation.nameEnRequired");
    if (!formData.id.trim() && !product) newErrors.id = t("validation.idRequired");
    if (!product && formData.id.trim() && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(formData.id)) {
      newErrors.id = t("validation.idFormat");
    }
    if (formData.price_cents <= 0) newErrors.price_cents = t("validation.pricePositive");
    if (!formData.product_type) newErrors.product_type = t("validation.productTypeRequired");
    if (formData.stock < 0) newErrors.stock = t("validation.stockNonNegative");
    if (images.length + formData.image_files.length > 6) {
      newErrors.image_files = t("validation.maxImages");
    }
    for (const file of formData.image_files) {
      const validType = ["image/jpeg", "image/png"].includes(file.type);
      if (!validType) newErrors.image_files = t("validation.imageType");
      if (file.size > MAX_IMAGE_SIZE) {
        newErrors.image_files = t("validation.imageSize");
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(formData);
      const successParam = product ? "updated" : "created";
      router.push(`/admin/products?success=${successParam}`);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.saveProduct"));
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateField<K extends keyof ProductFormData>(
    field: K,
    value: ProductFormData[K]
  ) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  }

  function syncImages(nextImages: ProductImage[], nextDeleted = deletedImageIds) {
    const normalizedImages = nextImages.some((image) => image.is_primary)
      ? nextImages
      : nextImages.map((image, index) => ({ ...image, is_primary: index === 0 }));
    setImages(normalizedImages);
    setFormData((prev) => ({
      ...prev,
      ordered_image_ids: normalizedImages.map((image) => image.id),
      deleted_image_ids: nextDeleted,
      primary_image_id:
        normalizedImages.find((image) => image.is_primary)?.id ?? normalizedImages[0]?.id ?? null,
    }));
  }

  function previewUrl(url: string): string {
    return url.startsWith("/static/") ? `${BASE_URL}${url}` : url;
  }

  function moveImage(index: number, direction: -1 | 1) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= images.length) return;
    const nextImages = [...images];
    const [image] = nextImages.splice(index, 1);
    if (!image) return;
    nextImages.splice(nextIndex, 0, image);
    syncImages(nextImages.map((item, sort_order) => ({ ...item, sort_order })));
  }

  function removeImage(imageId: string) {
    const nextDeleted = [...deletedImageIds, imageId];
    setDeletedImageIds(nextDeleted);
    syncImages(images.filter((image) => image.id !== imageId), nextDeleted);
  }

  function setPrimaryImage(imageId: string) {
    syncImages(images.map((image) => ({ ...image, is_primary: image.id === imageId })));
  }

  function addFiles(files: FileList | null) {
    if (!files) return;
    const nextFiles = [...formData.image_files, ...Array.from(files)].slice(0, 6 - images.length);
    updateField("image_files", nextFiles);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Product ID (only on create) */}
      {!product && (
        <Input
          label={t("productId")}
          placeholder={t("productIdPlaceholder")}
          value={formData.id}
          onChange={(e) => updateField("id", e.target.value)}
          error={errors.id}
        />
      )}

      {/* Dual-language name fields */}
      <div className="grid gap-6 sm:grid-cols-2">
        <div className="relative">
          <Input
            label={t("nameEn")}
            placeholder={t("nameEnPlaceholder")}
            value={formData.name_en}
            onChange={(e) => updateField("name_en", e.target.value)}
            error={errors.name_en}
          />
          {translationStaleEn && (
            <span className="absolute top-0 right-0 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-brand" title={t("translationStale")}>
              ⚠️
            </span>
          )}
        </div>
        <div className="relative">
          <Input
            label={t("nameBg")}
            placeholder={t("nameBgPlaceholder")}
            value={formData.name_bg}
            onChange={(e) => updateField("name_bg", e.target.value)}
          />
          {translationStaleBg && (
            <span className="absolute top-0 right-0 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-brand" title={t("translationStale")}>
              ⚠️
            </span>
          )}
        </div>
      </div>

      {/* Dual-language description fields */}
      <div className="grid gap-6 sm:grid-cols-2">
        <div className="relative">
          <label htmlFor="description_en" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("descriptionEn")}
          </label>
          <textarea
            id="description_en"
            value={formData.description_en}
            onChange={(e) => updateField("description_en", e.target.value)}
            rows={4}
            className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-soft-brown placeholder:text-soft-brown/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
            placeholder={t("descriptionEnPlaceholder")}
          />
          {translationStaleEn && (
            <span className="absolute top-0 right-0 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-brand" title={t("translationStale")}>
              ⚠️
            </span>
          )}
        </div>
        <div className="relative">
          <label htmlFor="description_bg" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("descriptionBg")}
          </label>
          <textarea
            id="description_bg"
            value={formData.description_bg}
            onChange={(e) => updateField("description_bg", e.target.value)}
            rows={4}
            className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-soft-brown placeholder:text-soft-brown/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
            placeholder={t("descriptionBgPlaceholder")}
          />
          {translationStaleBg && (
            <span className="absolute top-0 right-0 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded-brand" title={t("translationStale")}>
              ⚠️
            </span>
          )}
        </div>
      </div>

      {/* Other fields */}
      <div className="grid gap-6 sm:grid-cols-2">
        <div className="w-full">
          <label htmlFor="product_type" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("productType")}
          </label>
          <select
            id="product_type"
            value={formData.product_type}
            onChange={(e) => updateField("product_type", e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            <option value="">{t("selectProductType")}</option>
            {selectOptions(productTypes, formData.product_type).map((term) => (
              <option key={term.slug} value={term.slug}>
                {term.name_en}
                {!term.is_active ? ` ${t("retiredSuffix")}` : ""}
              </option>
            ))}
          </select>
          {errors.product_type && (
            <p className="mt-1.5 text-sm text-red-700">{errors.product_type}</p>
          )}
        </div>
        <div className="w-full">
          <label htmlFor="category" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("category")}
          </label>
          <select
            id="category"
            value={formData.category}
            onChange={(e) => updateField("category", e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            <option value="">{t("noCategoryOption")}</option>
            {selectOptions(categories, formData.category).map((term) => (
              <option key={term.slug} value={term.slug}>
                {term.name_en}
                {!term.is_active ? ` ${t("retiredSuffix")}` : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <span className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("labelsField")}
          </span>
          <p className="mb-2 text-xs text-soft-brown/70">{t("labelsHint")}</p>
          <div className="flex flex-wrap gap-2">
            {labelOptions.map((term) => {
              const checked = formData.labels.includes(term.slug);
              return (
                <label
                  key={term.slug}
                  className={cn(
                    "cursor-pointer rounded-pill px-3 py-1.5 text-sm focus-within:ring-2 focus-within:ring-soft-brown focus-within:ring-offset-2",
                    checked
                      ? "bg-muted-gold text-charcoal"
                      : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige"
                  )}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={(e) =>
                      updateField(
                        "labels",
                        e.target.checked
                          ? [...formData.labels, term.slug]
                          : formData.labels.filter((s) => s !== term.slug)
                      )
                    }
                  />
                  {term.name_en}
                  {!term.is_active ? ` ${t("retiredSuffix")}` : ""}
                </label>
              );
            })}
          </div>
        </div>
        <Input
          label={t("priceEur")}
          type="number"
          step="0.01"
          min="0"
          placeholder="0.00"
          value={priceDisplay}
          onChange={(e) => setPriceDisplay(e.target.value)}
          onBlur={(e) => {
            const cents = eurToCents(e.target.value);
            updateField("price_cents", cents);
            setPriceDisplay(cents > 0 ? (cents / 100).toFixed(2) : "");
          }}
          error={errors.price_cents}
        />
        <Input
          label={t("stock")}
          type="number"
          min="0"
          step="1"
          value={String(formData.stock)}
          onChange={(e) => updateField("stock", Math.max(0, Math.floor(Number(e.target.value) || 0)))}
          error={errors.stock}
        />
        <div className="sm:col-span-2 space-y-3">
          <label htmlFor="image_file" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("productImage")}
          </label>
          {images.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {images.map((image, index) => (
                <div key={image.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-2">
                  <div className="relative aspect-[4/5] w-full overflow-hidden rounded-brand">
                    <Image
                      src={previewUrl(image.thumbnail_url)}
                      alt=""
                      fill
                      sizes="160px"
                      className="object-cover"
                    />
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <Button type="button" variant="secondary" onClick={() => moveImage(index, -1)} disabled={index === 0}>
                      {t("moveUp")}
                    </Button>
                    <Button type="button" variant="secondary" onClick={() => moveImage(index, 1)} disabled={index === images.length - 1}>
                      {t("moveDown")}
                    </Button>
                    <Button type="button" variant={image.is_primary ? "primary" : "secondary"} onClick={() => setPrimaryImage(image.id)}>
                      {t("setPrimary")}
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => removeImage(image.id)}>
                      {tCommon("delete")}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <input
            id="image_file"
            type="file"
            accept="image/jpeg,image/png"
            multiple
            disabled={images.length + formData.image_files.length >= 6}
            onChange={(e) => addFiles(e.target.files)}
            className="block w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-sm text-soft-brown file:mr-4 file:rounded-brand file:border-0 file:bg-charcoal file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-warm-ivory hover:file:bg-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          />
          {errors.image_files && (
            <p className="mt-1.5 text-sm text-red-700">{errors.image_files}</p>
          )}
          {formData.image_files.length > 0 && (
            <p className="mt-1.5 text-xs text-soft-brown/70">
              {t("selectedFiles", { count: formData.image_files.length })}
            </p>
          )}
        </div>
        <Input
          label={t("materials")}
          placeholder={t("materialsPlaceholder")}
          value={formData.materials}
          onChange={(e) => updateField("materials", e.target.value)}
        />
        <Input
          label={t("daysToCraft")}
          type="number"
          min="1"
          placeholder={t("optional")}
          value={formData.days_to_craft !== null ? String(formData.days_to_craft) : ""}
          onChange={(e) => {
            const val = e.target.value ? parseInt(e.target.value) : null;
            updateField("days_to_craft", val);
          }}
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_featured"
          checked={formData.is_featured}
          onChange={(e) => updateField("is_featured", e.target.checked)}
          className="h-4 w-4 rounded border-champagne-beige text-muted-gold focus:ring-muted-gold"
        />
        <label htmlFor="is_featured" className="text-sm text-soft-brown">
          {t("featuredProduct")}
        </label>
      </div>

      <div className="flex items-center gap-3 border-t border-champagne-beige pt-6">
        <Button type="submit" isLoading={isSubmitting}>
          {submitLabel}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => router.push("/admin/products")}
        >
          {tCommon("cancel")}
        </Button>
      </div>
    </form>
  );
}
