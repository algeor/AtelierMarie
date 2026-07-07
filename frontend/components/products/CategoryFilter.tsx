"use client";

import { cn } from "@/lib/utils";

interface CategoryFilterProps {
  categories: string[];
  activeCategory: string;
  onCategoryChange: (category: string) => void;
  resultCount: number;
}

export function CategoryFilter({
  categories,
  activeCategory,
  onCategoryChange,
  resultCount,
}: CategoryFilterProps) {
  const allCategories = ["All", ...categories];

  // Hide filter if fewer than 2 total categories
  if (allCategories.length < 2) return null;

  const announcement =
    activeCategory === "All"
      ? `Showing ${resultCount} products`
      : `Showing ${resultCount} products in ${activeCategory}`;

  return (
    <div className="mb-8">
      <div
        role="group"
        aria-label="Filter by category"
        className="flex flex-nowrap md:flex-wrap gap-2 overflow-x-auto md:overflow-x-visible pb-2 md:pb-0 -mx-4 px-4 md:mx-0 md:px-0"
      >
        {allCategories.map((category) => {
          const isActive = category === activeCategory;
          return (
            <button
              key={category}
              onClick={() => onCategoryChange(category)}
              aria-pressed={isActive}
              className={cn(
                "shrink-0 px-4 py-2 rounded-pill text-sm font-medium transition-colors duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory",
                isActive
                  ? "bg-muted-gold text-charcoal"
                  : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige"
              )}
            >
              {category}
            </button>
          );
        })}
      </div>
      {/* Screen reader announcement for filter results */}
      <div aria-live="polite" role="status" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}
