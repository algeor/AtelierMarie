"use client";

import { useEffect, useMemo, useRef, type RefObject } from "react";
import { trackAnalytics, type AnalyticsEventPayload } from "@/lib/analytics";
import type { ProductResponse } from "@/lib/types";

type AnalyticsProperties = AnalyticsEventPayload["properties"];

export interface ProductDiscoveryContext {
  index?: number;
  listingContext?: string;
  activeFilters?: string;
  sort?: string;
  resultCount?: number;
  totalCount?: number;
}

function cleanText(value: string | null | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed.slice(0, 160) : undefined;
}

function buildDiscoveryProperties(
  product: ProductResponse,
  context: ProductDiscoveryContext,
): AnalyticsProperties {
  return {
    product_id: product.id,
    index: typeof context.index === "number" ? context.index : undefined,
    listing_context: cleanText(context.listingContext) ?? "product_grid",
    active_filters: cleanText(context.activeFilters),
    sort: cleanText(context.sort),
    product_type: cleanText(product.product_type),
    category: cleanText(product.category),
    result_count: typeof context.resultCount === "number" ? context.resultCount : undefined,
    total_count: typeof context.totalCount === "number" ? context.totalCount : undefined,
  };
}

function discoverySignature(product: ProductResponse, context: ProductDiscoveryContext) {
  return JSON.stringify({
    productId: product.id,
    index: context.index,
    listingContext: context.listingContext,
    activeFilters: context.activeFilters,
    sort: context.sort,
    resultCount: context.resultCount,
    totalCount: context.totalCount,
  });
}

export function useProductImpression(
  elementRef: RefObject<Element>,
  product: ProductResponse,
  context: ProductDiscoveryContext,
) {
  const trackedSignatureRef = useRef<string | null>(null);
  const signature = useMemo(
    () => discoverySignature(product, context),
    [
      context.activeFilters,
      context.index,
      context.listingContext,
      context.resultCount,
      context.sort,
      context.totalCount,
      product.id,
    ],
  );
  const properties = useMemo(
    () => buildDiscoveryProperties(product, context),
    [
      context.activeFilters,
      context.index,
      context.listingContext,
      context.resultCount,
      context.sort,
      context.totalCount,
      product.category,
      product.id,
      product.product_type,
    ],
  );

  useEffect(() => {
    const element = elementRef.current;
    if (!element || trackedSignatureRef.current === signature) return;

    const emit = () => {
      if (trackedSignatureRef.current === signature) return;
      trackAnalytics("product_impression", properties);
      trackedSignatureRef.current = signature;
    };

    if (typeof window === "undefined" || !("IntersectionObserver" in window)) {
      emit();
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        emit();
        observer.disconnect();
      },
      { threshold: 0.5 },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [elementRef, properties, signature]);
}

export function trackProductClick(
  product: ProductResponse,
  context: ProductDiscoveryContext,
  clickTarget: string,
) {
  trackAnalytics("product_click", {
    ...buildDiscoveryProperties(product, context),
    click_target: cleanText(clickTarget),
  });
}
