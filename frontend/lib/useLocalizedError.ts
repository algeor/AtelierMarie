import { useCallback } from "react";
import { useTranslations } from "next-intl";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

function getPathLocale(): "en" | "bg" {
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/bg")) {
    return "bg";
  }
  return "en";
}

function getStaticErrorMessage(code: string | undefined | null): string {
  const messages = getPathLocale() === "bg" ? bgMessages.errors : enMessages.errors;
  const key = code as keyof typeof messages | undefined | null;
  return (key && messages[key]) || messages.UNKNOWN;
}

/**
 * Hook to get localized error messages from API error codes.
 * Maps backend error codes (e.g., "INSUFFICIENT_STOCK") to user-facing
 * localized strings based on the active locale.
 *
 * The try/catch around `useTranslations` is intentional: some consumers
 * (e.g., CartContext) may be rendered in test setups without a
 * NextIntlClientProvider. Falling back to static messages keeps those
 * consumers working. Hook order is preserved because the same call
 * either succeeds or throws on every render.
 */
export function useLocalizedError() {
  let t: ReturnType<typeof useTranslations> | null = null;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    t = useTranslations("errors");
  } catch {
    t = null;
  }

  return useCallback(function getErrorMessage(code: string | undefined | null): string {
    if (!t) return getStaticErrorMessage(code);
    if (!code) return t("UNKNOWN");

    const messages = getPathLocale() === "bg" ? bgMessages.errors : enMessages.errors;
    if (code in messages) {
      return t(code as Parameters<typeof t>[0]);
    }
    return t("UNKNOWN");
  }, [t]);
}
