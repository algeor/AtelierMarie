"use client";

/**
 * Renders hreflang <link> tags for the alternate locale version of the current page.
 * Placed in the locale layout so it applies to all pages.
 */

import { usePathname } from "next/navigation";
import { locales } from "@/i18n/routing";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ateliermarie.com";

export function AlternateLinks() {
  const pathname = usePathname();

  // pathname looks like /en/products or /bg/products/lavender-dream
  // Strip the current locale prefix to get the path portion
  const pathWithoutLocale = pathname.replace(/^\/(en|bg)/, "") || "/";

  return (
    <>
      {locales.map((locale) => (
        <link
          key={locale}
          rel="alternate"
          hrefLang={locale}
          href={`${BASE_URL}/${locale}${pathWithoutLocale}`}
        />
      ))}
      <link
        rel="alternate"
        hrefLang="x-default"
        href={`${BASE_URL}/en${pathWithoutLocale}`}
      />
    </>
  );
}
