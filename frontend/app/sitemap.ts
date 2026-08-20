import type { MetadataRoute } from "next";
import { getProducts } from "@/lib/api";
import { locales, type Locale } from "@/i18n/routing";
import { HANDMADE_CANDLES_PATHS } from "@/lib/seo-pages";
import { BASE_URL, SEO } from "@/lib/seo";

const now = new Date();

/**
 * Public routes that should be discoverable in Google.
 * Private, transactional, and admin routes are intentionally omitted.
 */
const STATIC_ROUTES = [
  "",
  "/atelier",
  "/products",
  "/faq",
  "/contact",
  "/terms",
  "/privacy",
  "/cookies",
];

const LOCALIZED_ROUTES = [
  {
    paths: HANDMADE_CANDLES_PATHS,
    changeFrequency: "weekly" as const,
    priority: 0.85,
  },
];

async function getProductRoutes(locale: Locale) {
  try {
    const { products } = await getProducts(1, 100, locale, { in_stock: true });
    return products
      .filter((product) => product.is_active)
      .map((product) => ({
        path: `/products/${product.id}`,
        lastModified: product.updated_at ? new Date(product.updated_at) : now,
      }));
  } catch {
    return [];
  }
}

function alternateLanguages(path: string): Record<string, string> {
  const alternates: Record<string, string> = {};
  for (const locale of locales as readonly Locale[]) {
    alternates[locale] = `${BASE_URL}/${locale}${path}`;
  }
  alternates["x-default"] = `${BASE_URL}/${SEO.defaultLocale}${path}`;
  return alternates;
}

function localizedAlternateLanguages(paths: Record<Locale, string>): Record<string, string> {
  const alternates: Record<string, string> = {};
  for (const locale of locales as readonly Locale[]) {
    alternates[locale] = `${BASE_URL}/${locale}${paths[locale]}`;
  }
  alternates["x-default"] = `${BASE_URL}/${SEO.defaultLocale}${paths[SEO.defaultLocale]}`;
  return alternates;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];

  for (const route of STATIC_ROUTES) {
    for (const locale of locales) {
      entries.push({
        url: `${BASE_URL}/${locale}${route}`,
        lastModified: now,
        changeFrequency: route === "" || route === "/products" ? "weekly" : "monthly",
        priority: route === "" ? 1 : route === "/products" ? 0.9 : 0.6,
        alternates: {
          languages: alternateLanguages(route),
        },
      });
    }
  }

  for (const route of LOCALIZED_ROUTES) {
    for (const locale of locales) {
      entries.push({
        url: `${BASE_URL}/${locale}${route.paths[locale]}`,
        lastModified: now,
        changeFrequency: route.changeFrequency,
        priority: route.priority,
        alternates: {
          languages: localizedAlternateLanguages(route.paths),
        },
      });
    }
  }

  const productRoutesByLocale = await Promise.all(
    locales.map(async (locale) => ({
      locale,
      routes: await getProductRoutes(locale),
    })),
  );

  for (const { locale, routes } of productRoutesByLocale) {
    for (const route of routes) {
      entries.push({
        url: `${BASE_URL}/${locale}${route.path}`,
        lastModified: route.lastModified,
        changeFrequency: "weekly",
        priority: 0.8,
        alternates: {
          languages: alternateLanguages(route.path),
        },
      });
    }
  }

  return entries;
}
