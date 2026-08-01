"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  deleteProductImage,
  deleteProductVideo,
  getAdminProduct,
  getProductVideo,
  reorderProductImages,
  setPrimaryProductImage,
  updateProduct,
  updateProductVideoSortOrder,
  uploadProductImage,
  uploadProductVideo,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { ProductForm, type ProductFormData } from "@/components/admin/ProductForm";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import { Skeleton } from "@/components/ui/Skeleton";
import type { AdminProductResponse } from "@/lib/types";

export default function EditProductPage() {
  const t = useTranslations("admin");
  const getLocalizedError = useLocalizedError();
  const params = useParams();
  const productId = params.id as string;
  const [product, setProduct] = useState<AdminProductResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminProduct(productId)
      .then(setProduct)
      .catch((err) =>
        setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.loadProduct"))
      )
      .finally(() => setIsLoading(false));
  }, [productId, getLocalizedError, t]);

  useEffect(() => {
    const status = product?.video?.status;
    if (status !== "queued" && status !== "transcoding") return;

    let cancelled = false;
    async function pollVideo() {
      try {
        const video = await getProductVideo(productId);
        if (!cancelled) {
          setProduct((current) => (current ? { ...current, video } : current));
        }
      } catch (err) {
        if (!cancelled && err instanceof ApiError && err.code === "video_not_found") {
          setProduct((current) => (current ? { ...current, video: null } : current));
        }
      }
    }

    void pollVideo();
    const interval = window.setInterval(() => void pollVideo(), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [productId, product?.video?.status]);

  async function handleSubmit(data: ProductFormData) {
    await updateProduct(productId, {
      name_en: data.name_en,
      name_bg: data.name_bg || null,
      description_en: data.description_en || null,
      description_bg: data.description_bg || null,
      safety_warnings_en: data.safety_warnings_en || null,
      safety_warnings_bg: data.safety_warnings_bg || null,
      care_instructions_en: data.care_instructions_en || null,
      care_instructions_bg: data.care_instructions_bg || null,
      materials: data.materials || null,
      days_to_craft: data.days_to_craft,
      price_cents: data.price_cents,
      product_type: data.product_type,
      category: data.category || null,
      labels: data.labels,
      stock: data.stock,
      weight_grams: data.weight_grams,
      is_active: data.is_active,
      is_featured: data.is_featured,
      discount_percent: data.discount_percent,
      discount_starts_at: data.discount_starts_at,
      discount_ends_at: data.discount_ends_at,
    });
    for (const imageId of data.deleted_image_ids) {
      await deleteProductImage(productId, imageId);
    }
    if (data.ordered_image_ids.length > 0) {
      await reorderProductImages(productId, data.ordered_image_ids);
    }
    if (data.primary_image_id) {
      await setPrimaryProductImage(productId, data.primary_image_id);
    }
    for (const file of data.image_files) {
      await uploadProductImage(productId, file);
    }
    if (data.delete_video && product?.video) {
      await deleteProductVideo(productId);
    }
    if (data.video_file) {
      await uploadProductVideo(productId, data.video_file);
      await updateProductVideoSortOrder(productId, data.video_sort_order);
    } else if (product?.video && !data.delete_video) {
      await updateProductVideoSortOrder(productId, data.video_sort_order);
    }
  }

  if (isLoading) {
    return (
      <div>
        <Skeleton className="mb-2 h-8 w-48" />
        <Skeleton className="mb-8 h-4 w-64" />
        <div className="max-w-3xl space-y-4 rounded-brand border border-champagne-beige bg-cream p-6">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!product) return null;

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-2">
          <h1 className="font-heading text-2xl font-semibold text-charcoal">
            {t("editProduct")}
          </h1>
          <AdminInfoPopover content={t("editProductSubtitle", { name: product.name_en })} />
        </div>
      </div>

      <div className="max-w-3xl rounded-brand border border-champagne-beige bg-cream p-6">
        <ProductForm
          product={product}
          onSubmit={handleSubmit}
          submitLabel={t("saveChanges")}
        />
      </div>
    </div>
  );
}
