import type { MetadataRoute } from "next";
import { locales } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ateliermarie.com";

/**
 * Static routes that exist in both locales.
 * Dynamic product pages would be fetched from the API in production.
 */
const STATIC_ROUTES = [
  "",
  "/products",
  "/checkout",
  "/orders",
  "/account",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const entries: MetadataRoute.Sitemap = [];

  for (const route of STATIC_ROUTES) {
    for (const locale of locales) {
      const alternates: Record<string, string> = {};
      for (const alt of locales) {
        alternates[alt] = `${BASE_URL}/${alt}${route}`;
      }
      alternates["x-default"] = `${BASE_URL}/en${route}`;

      entries.push({
        url: `${BASE_URL}/${locale}${route}`,
        lastModified: new Date(),
        alternates: {
          languages: alternates,
        },
      });
    }
  }

  return entries;
}
