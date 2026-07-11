"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";

const STORAGE_KEY = "announcement_dismissed";

export function AnnouncementBar() {
  const t = useTranslations("announcement");
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(STORAGE_KEY) === "true") {
      setIsDismissed(true);
    }
  }, []);

  if (isDismissed) return null;

  function handleDismiss() {
    sessionStorage.setItem(STORAGE_KEY, "true");
    setIsDismissed(true);
  }

  return (
    <div className="bg-muted-gold/20 text-charcoal text-sm text-center py-2 px-4 relative">
      <p className="font-medium">{t("freeShipping")}</p>
      <button
        onClick={handleDismiss}
        className="absolute right-2 top-1/2 -translate-y-1/2 min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand text-charcoal/70 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
        aria-label={t("dismiss")}
      >
        <span aria-hidden="true" className="text-lg">×</span>
      </button>
    </div>
  );
}
