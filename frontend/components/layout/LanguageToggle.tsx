"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { updateLocalePreference } from "@/lib/api";

/**
 * Language toggle button showing the flag of the OTHER locale.
 * Clicking navigates to the equivalent page in the other language
 * and sets the NEXT_LOCALE cookie for persistence.
 */
export function LanguageToggle() {
  const t = useTranslations("locale");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();

  const otherLocale: Locale = locale === "bg" ? "en" : "bg";
  const flag = locale === "bg" ? "🇬🇧" : "🇧🇬";
  const label = locale === "bg" ? t("switchToEnglish") : t("switchToBulgarian");

  function handleToggle() {
    // Set cookie for persistence across visits
    document.cookie = `NEXT_LOCALE=${otherLocale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Lax`;

    // Navigate to same page in other locale
    router.replace(pathname, { locale: otherLocale });

    updateLocalePreference(otherLocale).catch(() => {
      // Non-critical — best effort
    });
  }

  return (
    <button
      onClick={handleToggle}
      aria-label={label}
      title={label}
      className="min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand text-xl transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
    >
      <span aria-hidden="true">{flag}</span>
    </button>
  );
}
