"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { ProductResponse } from "@/lib/types";
import { CategoryFilter } from "./CategoryFilter";
import { ProductGrid } from "./ProductGrid";
import { ProductCard } from "./ProductCard";

interface ProductListingClientProps {
  products: ProductResponse[];
}

export function ProductListingClient({ products }: ProductListingClientProps) {
  const t = useTranslations("products");
  const [activeCategory, setActiveCategory] = useState("All");

  // Derive unique non-null categories from product data
  const categories = Array.from(
    new Set(products.map((p) => p.category).filter((c): c is string => c !== null))
  );

  const filteredProducts =
    activeCategory === "All"
      ? products
      : products.filter((p) => p.category === activeCategory);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="font-heading text-3xl md:text-4xl text-charcoal mb-8">
        {t("title")}
      </h1>

      <CategoryFilter
        categories={categories}
        activeCategory={activeCategory}
        onCategoryChange={setActiveCategory}
        resultCount={filteredProducts.length}
      />

      {filteredProducts.length > 0 ? (
        <ProductGrid>
          {filteredProducts.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ProductGrid>
      ) : (
        <div className="text-center py-16">
          <p className="text-soft-brown text-lg">
            {t("noProducts")}
          </p>
        </div>
      )}
    </div>
  );
}
