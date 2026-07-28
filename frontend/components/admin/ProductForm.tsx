"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError, BASE_URL } from "@/lib/api-client";
import { formatPrice } from "@/lib/utils";
import type { AdminProductResponse, ProductImage } from "@/lib/types";
import { useLocalizedError } from "@/lib/useLocalizedError";

const CATEGORIES = ["Floral", "Woody", "Fresh", "Gourmand", "Spicy", "Citrus"];

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
  category: string;
  image_files: File[];
  ordered_image_ids: string[];
  deleted_image_ids: string[];
  primary_image_id: string | null;
  stock: number;
  weight_grams: number;
  is_active: boolean;
  is_featured: boolean;
  // Discount (percent 1–99 or null; datetimes are timezone-aware UTC ISO strings).
  discount_percent: number | null;
  discount_starts_at: string | null;
  discount_ends_at: string | null;
}

const MB = 1024 * 1024;
const MAX_IMAGE_SIZE = 25 * MB;
const LARGE_IMAGE_WARNING_SIZE = 15 * MB;

// Mirrors the backend MAX_WEIGHT_GRAMS bound (app/models/products.py).
const MAX_WEIGHT_GRAMS = 100_000;

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

/** Format a Date into a `datetime-local` input value (browser-local time). */
function toDatetimeLocal(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/** Stored UTC text (`YYYY-MM-DD HH:MM:SS`) → `datetime-local` value in local time. */
function storedUtcToLocalInput(utc: string | null): string {
  if (!utc) return "";
  const d = new Date(utc.replace(" ", "T") + "Z");
  return isNaN(d.getTime()) ? "" : toDatetimeLocal(d);
}

/** `datetime-local` value (local time) → timezone-aware UTC ISO string, or null. */
function localInputToUtcIso(local: string): string | null {
  if (!local) return null;
  const d = new Date(local);
  return isNaN(d.getTime()) ? null : d.toISOString();
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
  const [pendingImageFiles, setPendingImageFiles] = useState<File[] | null>(null);
  const largeImageDialogRef = useRef<HTMLDivElement>(null);
  const largeImageCancelRef = useRef<HTMLButtonElement>(null);

  // Local string state for price input to avoid cursor jumping
  const [priceDisplay, setPriceDisplay] = useState(
    product?.price_cents ? (product.price_cents / 100).toFixed(2) : ""
  );

  // Discount inputs — kept as local UI state; datetime pickers show local time
  // and are converted to timezone-aware UTC on submit.
  const [discountPercent, setDiscountPercent] = useState(
    product?.discount_percent != null ? String(product.discount_percent) : ""
  );
  const [discountStart, setDiscountStart] = useState(
    storedUtcToLocalInput(product?.discount_starts_at ?? null)
  );
  const [discountEnd, setDiscountEnd] = useState(
    storedUtcToLocalInput(product?.discount_ends_at ?? null)
  );

  // Local string state for weight so the field can be cleared / edited freely;
  // normalized and clamped on blur.
  const [weightDisplay, setWeightDisplay] = useState(
    String(product?.weight_grams ?? 300)
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
    category: product?.category ?? "",
    image_files: [],
    ordered_image_ids: (product?.images ?? []).map((image) => image.id),
    deleted_image_ids: [],
    primary_image_id: product?.images.find((image) => image.is_primary)?.id ?? null,
    stock: product?.stock ?? 0,
    weight_grams: product?.weight_grams ?? 300,
    is_active: product?.is_active ?? true,
    is_featured: product?.is_featured ?? false,
    discount_percent: product?.discount_percent ?? null,
    discount_starts_at: product?.discount_starts_at ?? null,
    discount_ends_at: product?.discount_ends_at ?? null,
  });

  const translationStaleBg = product?.translation_stale_bg;
  const translationStaleEn = product?.translation_stale_en;

  useEffect(() => {
    if (!pendingImageFiles) return;

    const previousActiveElement = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    largeImageCancelRef.current?.focus();
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPendingImageFiles(null);
        return;
      }
      if (event.key !== "Tab") return;

      const dialog = largeImageDialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      ));
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      // Re-capture focus if it has escaped the dialog (e.g. onto background content).
      if (!dialog.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previousActiveElement?.focus();
    };
  }, [pendingImageFiles]);

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!formData.name_en.trim()) newErrors.name_en = t("validation.nameEnRequired");
    if (!formData.id.trim() && !product) newErrors.id = t("validation.idRequired");
    if (!product && formData.id.trim() && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(formData.id)) {
      newErrors.id = t("validation.idFormat");
    }
    if (formData.price_cents <= 0) newErrors.price_cents = t("validation.pricePositive");
    if (!formData.category) newErrors.category = t("validation.categoryRequired");
    if (formData.stock < 0) newErrors.stock = t("validation.stockNonNegative");
    if (formData.weight_grams < 1 || formData.weight_grams > MAX_WEIGHT_GRAMS) {
      newErrors.weight_grams = t("validation.weightRange");
    }
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
    // Discount validation (client-side mirror of the server rules).
    const percentStr = discountPercent.trim();
    if (percentStr) {
      const percent = Number(percentStr);
      if (!Number.isInteger(percent) || percent < 1 || percent > 99) {
        newErrors.discount_percent = t("validation.discountPercentRange");
      }
      if (discountStart && discountEnd && new Date(discountStart) >= new Date(discountEnd)) {
        newErrors.discount_window = t("validation.discountWindowOrder");
      }
    } else if (discountStart || discountEnd) {
      newErrors.discount_percent = t("validation.discountPercentRequired");
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (pendingImageFiles) return;
    if (!validate()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      // Leaving percent empty clears the discount and both bounds together.
      const percentStr = discountPercent.trim();
      const discountFields = !percentStr
        ? { discount_percent: null, discount_starts_at: null, discount_ends_at: null }
        : {
            discount_percent: Number(percentStr),
            discount_starts_at: localInputToUtcIso(discountStart),
            discount_ends_at: localInputToUtcIso(discountEnd),
          };
      await onSubmit({ ...formData, ...discountFields });
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

  function formatFileSizeMb(bytes: number): string {
    return (bytes / MB).toFixed(1);
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

  function commitFiles(files: File[]) {
    updateField("image_files", [...formData.image_files, ...files].slice(0, 6 - images.length));
  }

  function addFiles(files: FileList | null) {
    if (!files) return;
    const availableSlots = 6 - images.length - formData.image_files.length;
    const selectedFiles = Array.from(files).slice(0, availableSlots);
    if (selectedFiles.length === 0) return;

    if (selectedFiles.some((file) => file.size > MAX_IMAGE_SIZE)) {
      setErrors((prev) => ({ ...prev, image_files: t("validation.imageSize") }));
      return;
    }

    if (selectedFiles.some((file) => file.size >= LARGE_IMAGE_WARNING_SIZE)) {
      setPendingImageFiles(selectedFiles);
      return;
    }

    commitFiles(selectedFiles);
  }

  const pendingLargestImageSize = pendingImageFiles
    ? Math.max(...pendingImageFiles.map((file) => file.size))
    : 0;

  const percentNum = Number(discountPercent);
  const showDiscountPreview =
    discountPercent.trim() !== "" &&
    Number.isInteger(percentNum) &&
    percentNum >= 1 &&
    percentNum <= 99 &&
    formData.price_cents > 0;
  const discountPreviewCents = showDiscountPreview
    ? Math.max(1, Math.floor((formData.price_cents * (100 - percentNum) + 50) / 100))
    : 0;

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
          <label htmlFor="category" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("category")}
          </label>
          <select
            id="category"
            value={formData.category}
            onChange={(e) => updateField("category", e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            <option value="">{t("selectCategory")}</option>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          {errors.category && (
            <p className="mt-1.5 text-sm text-red-700">{errors.category}</p>
          )}
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
        <div className="w-full">
          <Input
            label={t("weightGrams")}
            type="number"
            min="1"
            max={String(MAX_WEIGHT_GRAMS)}
            step="1"
            value={weightDisplay}
            onChange={(e) => setWeightDisplay(e.target.value)}
            onBlur={(e) => {
              const parsed = Math.floor(Number(e.target.value));
              const clamped =
                Number.isFinite(parsed) && parsed >= 1
                  ? Math.min(MAX_WEIGHT_GRAMS, parsed)
                  : formData.weight_grams;
              updateField("weight_grams", clamped);
              setWeightDisplay(String(clamped));
            }}
            error={errors.weight_grams}
          />
          <p className="mt-1.5 text-xs text-soft-brown/70">{t("weightGramsHelp")}</p>
        </div>
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
            onChange={(e) => {
              addFiles(e.target.files);
              e.currentTarget.value = "";
            }}
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
          {pendingImageFiles && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/60 p-4"
              onMouseDown={(event) => {
                if (event.target === event.currentTarget) setPendingImageFiles(null);
              }}
            >
              <div
                ref={largeImageDialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="large-image-title"
                aria-describedby="large-image-desc"
                className="w-full max-w-md rounded-brand bg-warm-ivory p-5 shadow-lg"
              >
                <h2 id="large-image-title" className="font-heading text-lg text-charcoal">
                  {t("largeImageTitle")}
                </h2>
                <p id="large-image-desc" className="mt-2 text-sm text-soft-brown">
                  {t("largeImageWarning", {
                    size: formatFileSizeMb(pendingLargestImageSize),
                  })}
                </p>
                <div className="mt-5 flex justify-end gap-2">
                  <Button
                    ref={largeImageCancelRef}
                    type="button"
                    variant="secondary"
                    onClick={() => setPendingImageFiles(null)}
                  >
                    {tCommon("cancel")}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => {
                      commitFiles(pendingImageFiles);
                      setPendingImageFiles(null);
                    }}
                  >
                    {t("addAnyway")}
                  </Button>
                </div>
              </div>
            </div>
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

      {/* Discount */}
      <div className="space-y-4 rounded-brand border border-champagne-beige p-4">
        <div>
          <h2 className="font-heading text-lg text-charcoal">{t("discount.title")}</h2>
          <p className="mt-1 text-xs text-soft-brown/70">{t("discount.help")}</p>
        </div>
        <div className="grid gap-6 sm:grid-cols-3">
          <Input
            label={t("discount.percent")}
            type="number"
            min="1"
            max="99"
            step="1"
            placeholder={t("optional")}
            value={discountPercent}
            onChange={(e) => {
              setDiscountPercent(e.target.value);
              setErrors((prev) => {
                const next = { ...prev };
                delete next.discount_percent;
                return next;
              });
            }}
            error={errors.discount_percent}
          />
          <div className="w-full">
            <label
              htmlFor="discount_starts_at"
              className="mb-1.5 block text-sm font-medium text-soft-brown"
            >
              {t("discount.startsAt")}
            </label>
            <input
              id="discount_starts_at"
              type="datetime-local"
              value={discountStart}
              onChange={(e) => setDiscountStart(e.target.value)}
              className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
            />
          </div>
          <div className="w-full">
            <label
              htmlFor="discount_ends_at"
              className="mb-1.5 block text-sm font-medium text-soft-brown"
            >
              {t("discount.endsAt")}
            </label>
            <input
              id="discount_ends_at"
              type="datetime-local"
              value={discountEnd}
              onChange={(e) => setDiscountEnd(e.target.value)}
              className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
            />
          </div>
        </div>
        {errors.discount_window && (
          <p className="text-sm text-red-700">{errors.discount_window}</p>
        )}
        {showDiscountPreview && (
          <p className="text-sm text-soft-brown">
            {t("discount.preview", { price: formatPrice(discountPreviewCents) })}
          </p>
        )}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          checked={formData.is_active}
          onChange={(e) => updateField("is_active", e.target.checked)}
          className="h-4 w-4 rounded border-champagne-beige text-muted-gold focus:ring-muted-gold"
        />
        <label htmlFor="is_active" className="text-sm text-soft-brown">
          {t("activeProduct")}
        </label>
      </div>

      <div className="flex items-center gap-3 border-t border-champagne-beige pt-6">
        <Button type="submit" isLoading={isSubmitting} disabled={Boolean(pendingImageFiles)}>
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
