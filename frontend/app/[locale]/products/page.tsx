import { getProducts, getTaxonomy } from "@/lib/api";
import { ProductListingClient } from "@/components/products/ProductListingClient";
import type { Locale } from "@/i18n/routing";
import type { Metadata } from "next";
import type { ProductListQuery, ProductListSort } from "@/lib/types";
import { getLocalizedAlternates } from "@/lib/seo";

const DEFAULT_PRODUCT_LIMIT = 24;
const MAX_PRODUCT_LIMIT = 100;
const MAX_LABEL_FILTERS = 12;
const PRODUCT_SORTS = new Set<ProductListSort>([
  "price_asc",
  "price_desc",
  "name",
  "newest",
]);

type ProductSearchParams = Record<string, string | string[] | undefined>;

interface ProductsPageProps {
  params: Promise<{ locale: Locale }>;
  searchParams?: Promise<ProductSearchParams>;
}

interface NormalizedProductListingParams {
  page: number;
  limit: number;
  query: ProductListQuery;
  path: string;
}

function valuesFor(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) return value;
  return value === undefined ? [] : [value];
}

function firstValue(value: string | string[] | undefined): string | undefined {
  return valuesFor(value)[0];
}

function cleanValue(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

function positiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) return fallback;
  return parsed;
}

function booleanFilter(value: string | undefined): boolean | undefined {
  if (value === "1" || value === "true") return true;
  if (value === "0" || value === "false") return false;
  return undefined;
}

function labelFilters(params: ProductSearchParams): string[] | undefined {
  const labels: string[] = [];
  for (const raw of [
    ...valuesFor(params.labels),
    ...valuesFor(params.label),
  ]) {
    for (const part of raw.split(",")) {
      const label = cleanValue(part);
      if (label && !labels.includes(label)) labels.push(label);
      if (labels.length >= MAX_LABEL_FILTERS) return labels;
    }
  }
  return labels.length ? labels : undefined;
}

function normalizeProductListingParams(
  params: ProductSearchParams = {},
): NormalizedProductListingParams {
  const page = positiveInt(firstValue(params.page), 1);
  const limit = Math.min(
    positiveInt(firstValue(params.limit), DEFAULT_PRODUCT_LIMIT),
    MAX_PRODUCT_LIMIT,
  );
  const sort = cleanValue(firstValue(params.sort));
  const query: ProductListQuery = {
    product_type:
      cleanValue(firstValue(params.product_type)) ??
      cleanValue(firstValue(params.type)),
    category: cleanValue(firstValue(params.category)),
    labels: labelFilters(params),
    q: cleanValue(firstValue(params.q)),
    sort:
      sort && PRODUCT_SORTS.has(sort as ProductListSort)
        ? (sort as ProductListSort)
        : undefined,
    in_stock: booleanFilter(firstValue(params.in_stock)),
  };

  const canonical = new URLSearchParams();
  if (query.product_type) canonical.set("type", query.product_type);
  if (query.category) canonical.set("category", query.category);
  if (query.labels?.length) canonical.set("labels", query.labels.join(","));
  if (query.in_stock) canonical.set("in_stock", "1");
  if (query.q) canonical.set("q", query.q);
  if (query.sort) canonical.set("sort", query.sort);
  if (page > 1) canonical.set("page", String(page));
  if (limit !== DEFAULT_PRODUCT_LIMIT) canonical.set("limit", String(limit));

  const qs = canonical.toString();
  return {
    page,
    limit,
    query,
    path: qs ? `/products?${qs}` : "/products",
  };
}

function titleForListing(query: ProductListQuery): string {
  if (query.q) return `${query.q} | Our Collection`;
  const primary = query.category ?? query.product_type;
  if (!primary) return "Our Collection";
  const label = primary
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return `${label} | Our Collection`;
}

function descriptionForListing(locale: Locale, query: ProductListQuery): string {
  if (query.q) {
    return locale === "bg"
      ? `Разгледайте резултати за ${query.q} в ръчно изработената колекция на Ателие Мари.`
      : `Browse results for ${query.q} in Atelier Marie's handmade collection.`;
  }
  return locale === "bg"
    ? "Разгледайте ръчно изработени свещи, персонални подаръци, тефтери и сезонни изделия от Ателие Мари."
    : "Shop handmade candles, custom gifts, notebooks, and seasonal pieces from Atelier Marie.";
}

export async function generateMetadata({
  params,
  searchParams,
}: ProductsPageProps): Promise<Metadata> {
  const { locale } = await params;
  const normalized = normalizeProductListingParams(await searchParams);
  return {
    title: titleForListing(normalized.query),
    description: descriptionForListing(locale, normalized.query),
    alternates: getLocalizedAlternates(locale, normalized.path),
  };
}

export default async function ProductsPage({
  params,
  searchParams,
}: ProductsPageProps) {
  const { locale } = await params;
  const normalized = normalizeProductListingParams(await searchParams);
  // Products drive the primary "sell candles" page; taxonomy only builds the
  // filter menu. Fetch them independently so a taxonomy endpoint failure
  // degrades the menu (empty facets) instead of taking down the product grid.
  const [{ products, total, page, limit }, taxonomy] = await Promise.all([
    getProducts(normalized.page, normalized.limit, locale, normalized.query),
    getTaxonomy(locale).catch(() => ({
      product_types: [],
      categories: [],
      labels: [],
    })),
  ]);

  return (
    <main>
      <ProductListingClient
        products={products}
        taxonomy={taxonomy}
        total={total}
        page={page}
        limit={limit}
        filters={normalized.query}
      />
    </main>
  );
}
