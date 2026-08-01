"use client";

import { useEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { updateLocalePreference } from "@/lib/api";

type LocaleOption = {
  code: Locale;
  flag: string;
};

const LOCALES: readonly LocaleOption[] = [
  { code: "bg", flag: "🇧🇬" },
  { code: "en", flag: "🇬🇧" },
] as const;

/**
 * Language dropdown showing the flag of the CURRENT locale on the trigger,
 * and both locales inside the menu (active one marked with a check).
 * Selecting a language navigates to the equivalent page and persists the
 * choice via cookie + backend sync.
 */
export function LanguageToggle() {
  const t = useTranslations("locale");
  const currentLocale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();

  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const current =
    LOCALES.find((l) => l.code === currentLocale) ?? LOCALES[0]!;

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Close on Escape and return focus to trigger
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function handleSelect(target: Locale) {
    setIsOpen(false);

    if (target === currentLocale) {
      return;
    }

    // Set cookie for persistence across visits
    document.cookie = `NEXT_LOCALE=${target};path=/;max-age=${60 * 60 * 24 * 365};SameSite=Lax`;

    // Navigate to the same page in the other locale
    router.replace(pathname, { locale: target });

    updateLocalePreference(target).catch(() => {
      // Non-critical — best effort
    });
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={t("changeLanguage")}
        className="min-w-[44px] min-h-[44px] inline-flex items-center justify-center gap-1.5 px-2 rounded-brand transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
      >
        <span aria-hidden="true" className="text-xl leading-none">
          {current.flag}
        </span>
        <span
          aria-hidden="true"
          className="text-xs font-medium uppercase tracking-wide text-charcoal"
        >
          {current.code.toUpperCase()}
        </span>
        <span
          aria-hidden="true"
          className={`text-xs text-soft-brown transition-transform duration-fast ${
            isOpen ? "rotate-180" : ""
          }`}
        >
          ▾
        </span>
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-label={t("changeLanguage")}
          className="absolute right-0 mt-2 w-44 rounded-brand bg-white shadow-lg ring-1 ring-black/5 py-1 z-50"
        >
          {LOCALES.map((option) => {
            const isActive = option.code === currentLocale;
            const itemLabel =
              option.code === "en"
                ? t("switchToEnglish")
                : t("switchToBulgarian");
            const optionName =
              option.code === "en" ? t("english") : t("bulgarian");
            return (
              <button
                key={option.code}
                role="menuitem"
                type="button"
                onClick={() => handleSelect(option.code)}
                aria-current={isActive ? "true" : undefined}
                aria-label={itemLabel}
                className={`flex w-full items-center gap-3 px-4 py-2 text-sm text-charcoal transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:bg-cream ${
                  isActive ? "bg-cream" : ""
                }`}
              >
                <span aria-hidden="true" className="text-lg leading-none">
                  {option.flag}
                </span>
                <span className="flex-1 text-left">{optionName}</span>
                {isActive && (
                  <span
                    aria-hidden="true"
                    className="text-soft-brown text-sm"
                  >
                    ✓
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
