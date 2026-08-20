/**
 * SEO utilities for bilingual hreflang generation.
 */

import { locales, type Locale } from "@/i18n/routing";
import { INSTAGRAM_URL, TIKTOK_URL } from "@/lib/social";
import type { FaqSectionResponse, ProductResponse } from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ateliermarie.com";
const BRAND_NAME = "Atelier Marie";
const DEFAULT_LOCALE: Locale = "en";
const SITE_DESCRIPTION =
  "Handmade candles, custom gifts, notebooks, and seasonal pieces prepared with care by Atelier Marie.";

export const SEO = {
  brandName: BRAND_NAME,
  siteDescription: SITE_DESCRIPTION,
  defaultLocale: DEFAULT_LOCALE,
};

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
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const locale of locales) {
    result[locale] = `${BASE_URL}/${locale}${pathname}`;
  }
  result["x-default"] = `${BASE_URL}/${SEO.defaultLocale}${pathname}`;
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

export function getLocalizedPathAlternates(
  locale: Locale,
  paths: Record<Locale, string>,
) {
  const languages: Record<string, string> = {};
  for (const altLocale of locales as readonly Locale[]) {
    languages[altLocale] = `${BASE_URL}/${altLocale}${paths[altLocale]}`;
  }
  languages["x-default"] = `${BASE_URL}/${SEO.defaultLocale}${paths[SEO.defaultLocale]}`;

  return {
    languages,
    canonical: `${BASE_URL}/${locale}${paths[locale]}`,
  };
}

export function getAboutJsonLd(locale: Locale) {
  const url = getCanonicalUrl(locale, "/atelier");
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${BASE_URL}/#organization`,
        name: "The Atelier Marie",
        url: BASE_URL,
      },
      {
        "@type": "AboutPage",
        "@id": `${url}#about-page`,
        url,
        name: "The Atelier Marie Atelier Story",
        inLanguage: locale,
        about: { "@id": `${BASE_URL}/#organization` },
      },
    ],
  };
}

export function getSiteJsonLd(locale: Locale) {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${BASE_URL}/#organization`,
        name: BRAND_NAME,
        alternateName: "The Atelier Marie",
        url: BASE_URL,
        email: "contacts@theateliermarie.com",
        sameAs: [INSTAGRAM_URL, TIKTOK_URL],
      },
      {
        "@type": "WebSite",
        "@id": `${BASE_URL}/#website`,
        url: BASE_URL,
        name: BRAND_NAME,
        description: SITE_DESCRIPTION,
        inLanguage: locale,
        publisher: { "@id": `${BASE_URL}/#organization` },
      },
    ],
  };
}

export function serializeJsonLd(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

export function buildFaqJsonLd(sections: FaqSectionResponse[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: sections.flatMap((section) =>
      section.items.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: item.answer,
        },
      }))
    ),
  };
}

function absoluteUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  return `${BASE_URL}${url.startsWith("/") ? url : `/${url}`}`;
}

export function buildProductJsonLd(product: ProductResponse, locale: Locale) {
  const productUrl = getCanonicalUrl(locale, `/products/${product.id}`);
  const imageUrls = [
    ...product.images.map((image) => image.zoom_url ?? image.image_url),
    product.primary_image_url,
  ]
    .filter((url): url is string => Boolean(url))
    .map(absoluteUrl);

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    "@id": `${productUrl}#product`,
    name: product.name,
    description: product.description ?? undefined,
    image: Array.from(new Set(imageUrls)),
    sku: product.id,
    productID: product.id,
    brand: {
      "@type": "Brand",
      name: "Atelier Marie",
    },
    offers: {
      "@type": "Offer",
      url: productUrl,
      price: (product.effective_price_cents / 100).toFixed(2),
      priceCurrency: "EUR",
      availability:
        product.stock > 0
          ? "https://schema.org/InStock"
          : "https://schema.org/OutOfStock",
      itemCondition: "https://schema.org/NewCondition",
      seller: {
        "@type": "Organization",
        name: "Atelier Marie",
      },
    },
  };
}

export { BASE_URL };
