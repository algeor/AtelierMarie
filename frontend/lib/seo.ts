/**
 * SEO utilities for bilingual hreflang generation.
 */

import { locales, type Locale } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ateliermarie.com";

/**
 * Generate hreflang alternate links for a given pathname.
 * Returns an object suitable for Next.js metadata `alternates.languages`.
 *
 * Example:
 *   getAlternateLanguages("/products") =>
 *   { en: "https://ateliermarie.com/en/products", bg: "https://ateliermarie.com/bg/products" }
 */
export function getAlternateLanguages(
  pathname: string
): Record<Locale, string> {
  const result = {} as Record<Locale, string>;
  for (const locale of locales) {
    result[locale] = `${BASE_URL}/${locale}${pathname}`;
  }
  return result;
}

/**
 * Get the canonical URL for a locale + pathname combination.
 */
export function getCanonicalUrl(locale: Locale, pathname: string): string {
  return `${BASE_URL}/${locale}${pathname}`;
}

export function getLocalizedAlternates(locale: Locale, pathname: string) {
  return {
    languages: getAlternateLanguages(pathname),
    canonical: getCanonicalUrl(locale, pathname),
  };
}

export { BASE_URL };
