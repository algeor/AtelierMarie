"use client";

import { useTranslations } from "next-intl";
import { createProduct, uploadProductImage } from "@/lib/api";
import { ProductForm, type ProductFormData } from "@/components/admin/ProductForm";

export default function CreateProductPage() {
  const t = useTranslations("admin");

  async function handleSubmit(data: ProductFormData) {
    const product = await createProduct({
      id: data.id,
      name_en: data.name_en,
      name_bg: data.name_bg || null,
      description_en: data.description_en || null,
      description_bg: data.description_bg || null,
      materials: data.materials || null,
      days_to_craft: data.days_to_craft,
      price_cents: data.price_cents,
      category: data.category,
      stock: data.stock,
      weight_grams: data.weight_grams,
      is_active: data.is_active,
      is_featured: data.is_featured,
    });
    for (const file of data.image_files) {
      await uploadProductImage(product.id, file);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">
          {t("createProduct")}
        </h1>
        <p className="mt-1 text-sm text-soft-brown">
          {t("createProductSubtitle")}
        </p>
      </div>

      <div className="max-w-3xl rounded-brand border border-champagne-beige bg-cream p-6">
        <ProductForm onSubmit={handleSubmit} submitLabel={t("createProduct")} />
      </div>
    </div>
  );
}
