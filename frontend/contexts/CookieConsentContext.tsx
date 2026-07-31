"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname } from "@/i18n/navigation";
import {
  CONSENT_VERSION,
  clearAnalyticsQueue,
  readConsentPreference,
  setAnalyticsConsent,
  syncConsentPreference,
  writeConsentPreference,
} from "@/lib/analytics";
import { policyPath } from "@/lib/legal";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";

interface CookieConsentContextValue {
  analytics: boolean;
  hasChoice: boolean;
  openSettings: () => void;
  acceptAnalytics: () => void;
  necessaryOnly: () => void;
}

const CookieConsentContext = createContext<CookieConsentContextValue | null>(null);

export function CookieConsentProvider({ children }: { children: React.ReactNode }) {
  const locale = useLocale() as "en" | "bg";
  const pathname = usePathname();
  const t = useTranslations("cookieConsent");
  const [analytics, setAnalytics] = useState(false);
  const [hasChoice, setHasChoice] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const isAdmin = pathname.startsWith("/admin");

  useEffect(() => {
    let cancelled = false;
    const preference = readConsentPreference();
    const current = preference?.version === CONSENT_VERSION;
    setAnalytics(false);
    setAnalyticsConsent(false);
    if (!current || !preference) {
      setHasChoice(false);
      return () => {
        cancelled = true;
      };
    }
    setHasChoice(true);
    void syncConsentPreference(preference.analytics, preference.locale)
      .then(() => {
        if (cancelled) return;
        setAnalytics(preference.analytics);
        setAnalyticsConsent(preference.analytics);
      })
      .catch(() => {
        if (cancelled) return;
        setAnalytics(false);
        setAnalyticsConsent(false);
        if (preference.analytics) setHasChoice(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const saveChoice = useCallback(
    async (allowed: boolean) => {
      setAnalyticsConsent(false);
      clearAnalyticsQueue();
      try {
        await syncConsentPreference(allowed, locale);
      } catch {
        writeConsentPreference(false, locale);
        setAnalytics(false);
        setHasChoice(false);
        setSettingsOpen(true);
        return;
      }
      writeConsentPreference(allowed, locale);
      setAnalyticsConsent(allowed);
      setAnalytics(allowed);
      setHasChoice(true);
      setSettingsOpen(false);
    },
    [locale]
  );

  useEffect(() => {
    const open = () => setSettingsOpen(true);
    window.addEventListener("open-cookie-settings", open);
    return () => window.removeEventListener("open-cookie-settings", open);
  }, []);

  const value = useMemo<CookieConsentContextValue>(
    () => ({
      analytics,
      hasChoice,
      openSettings: () => setSettingsOpen(true),
      acceptAnalytics: () => saveChoice(true),
      necessaryOnly: () => saveChoice(false),
    }),
    [analytics, hasChoice, saveChoice]
  );

  const showPopup = !isAdmin && (!hasChoice || settingsOpen);

  return (
    <CookieConsentContext.Provider value={value}>
      {children}
      {showPopup && (
        <div className="fixed inset-x-0 bottom-0 z-[120] px-4 pb-4 sm:px-6" role="region" aria-label={t("title")}>
          <div className="mx-auto max-w-3xl rounded-brand border border-champagne-beige bg-cream p-4 shadow-xl shadow-charcoal/15 sm:p-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <h2 className="font-heading text-lg text-charcoal">{t("title")}</h2>
                <p className="mt-2 text-sm leading-6 text-soft-brown">{t("body")}</p>
                <Link
                  href={policyPath("cookies")}
                  className="mt-2 inline-flex text-sm font-medium text-soft-brown underline underline-offset-4 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                >
                  {t("policyLink")}
                </Link>
              </div>
              <div className="flex shrink-0 flex-col gap-2 sm:min-w-48">
                <button
                  type="button"
                  onClick={() => void saveChoice(true)}
                  className="rounded-brand bg-muted-gold px-4 py-2.5 text-sm font-semibold text-charcoal transition-colors hover:bg-muted-gold/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                >
                  {t("accept")}
                </button>
                <button
                  type="button"
                  onClick={() => void saveChoice(false)}
                  className="rounded-brand border border-champagne-beige px-4 py-2.5 text-sm font-semibold text-soft-brown transition-colors hover:bg-champagne-beige/50 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                >
                  {t("necessary")}
                </button>
                {settingsOpen && (
                  <button
                    type="button"
                    onClick={() => setSettingsOpen(false)}
                    className={cn(
                      "rounded-brand px-4 py-2 text-sm text-soft-brown underline underline-offset-4",
                      "hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                    )}
                  >
                    {t("close")}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </CookieConsentContext.Provider>
  );
}

export function useCookieConsent() {
  const context = useContext(CookieConsentContext);
  if (!context) {
    throw new Error("useCookieConsent must be used within CookieConsentProvider");
  }
  return context;
}
