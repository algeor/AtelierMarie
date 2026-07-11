import { useCallback } from "react";
import { useTranslations } from "next-intl";

/**
 * Hook to get localized error messages from API error codes.
 * Maps backend error codes (e.g., "INSUFFICIENT_STOCK") to user-facing
 * localized strings based on the active locale.
 */
export function useLocalizedError() {
  const t = useTranslations("errors");

  return useCallback(function getErrorMessage(code: string | undefined | null): string {
    if (!code) return t("UNKNOWN");

    // Try to find the error code in translations; fall back to UNKNOWN
    try {
      return t(code as Parameters<typeof t>[0]);
    } catch {
      return t("UNKNOWN");
    }
  }, [t]);
}
