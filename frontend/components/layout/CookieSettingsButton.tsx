"use client";

import { useTranslations } from "next-intl";

export function CookieSettingsButton() {
  const t = useTranslations("cookieConsent");
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("open-cookie-settings"))}
      className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
    >
      {t("settingsLink")}
    </button>
  );
}
