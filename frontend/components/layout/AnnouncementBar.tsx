"use client";

import { useState, useEffect } from "react";
import { useLocale, useTranslations } from "next-intl";
import { getPublicBanner } from "@/lib/api";
import type { Locale } from "@/i18n/routing";
import type { PublicBanner } from "@/lib/types";

// Dismissals are keyed by the banner's dismiss_key (which changes when admins
// edit the message or schedule), so an edited banner reappears after a prior
// dismissal of older copy.
const STORAGE_KEY = "announcement_dismissed_key";

export function AnnouncementBar() {
  const t = useTranslations("announcement");
  const locale = useLocale() as Locale;
  const [banner, setBanner] = useState<PublicBanner | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getPublicBanner(locale)
      .then((res) => {
        if (cancelled) return;
        setBanner(res.banner);
        if (
          res.banner &&
          localStorage.getItem(STORAGE_KEY) === res.banner.dismiss_key
        ) {
          setDismissed(true);
        } else {
          setDismissed(false);
        }
      })
      .catch(() => {
        // Non-critical: on error, simply render no banner.
      });
    return () => {
      cancelled = true;
    };
  }, [locale]);

  if (!banner || dismissed) return null;

  function handleDismiss() {
    if (banner) localStorage.setItem(STORAGE_KEY, banner.dismiss_key);
    setDismissed(true);
  }

  return (
    <div className="relative bg-muted-gold/20 px-10 py-2 text-center text-sm text-charcoal">
      <p className="font-medium">
        {banner.message}
        {banner.link_url && (
          <>
            {" "}
            <a
              href={banner.link_url}
              className="underline underline-offset-2 hover:text-charcoal/80"
            >
              {banner.link_label ?? banner.link_url}
            </a>
          </>
        )}
      </p>
      <button
        onClick={handleDismiss}
        className="absolute right-2 top-1/2 inline-flex min-h-[44px] min-w-[44px] -translate-y-1/2 items-center justify-center rounded-brand text-charcoal/70 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
        aria-label={t("dismiss")}
      >
        <span aria-hidden="true" className="text-lg">
          ×
        </span>
      </button>
    </div>
  );
}
