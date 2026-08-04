"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface CookieSettingsButtonProps {
  className?: string;
}

export function CookieSettingsButton({ className }: CookieSettingsButtonProps) {
  const t = useTranslations("cookieConsent");
  const hasCustomClassName = Boolean(className);

  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("open-cookie-settings"))}
      className={cn(
        !hasCustomClassName && "text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5",
        className
      )}
    >
      {t("settingsLink")}
    </button>
  );
}
