/**
 * Tests for LanguageToggle component.
 *
 * Verifies:
 * - Renders correct flag for opposite locale
 * - Sets NEXT_LOCALE cookie on click
 * - Navigates to the same page in the other locale
 * - Sends locale preference update to backend
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockReplace = vi.fn();
const mockPathname = "/products";

vi.mock("next-intl", () => ({
  useLocale: vi.fn(() => "en"),
  useTranslations: vi.fn(() => (key: string) => {
    const translations: Record<string, string> = {
      switchToBulgarian: "Превключи на български",
      switchToEnglish: "Switch to English",
    };
    return translations[key] ?? key;
  }),
}));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => mockPathname,
}));

import { useLocale } from "next-intl";
import { LanguageToggle } from "@/components/layout/LanguageToggle";

const mockedUseLocale = vi.mocked(useLocale);

describe("LanguageToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset cookie
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });
    // Mock fetch for locale preference update
    global.fetch = vi.fn().mockResolvedValue({ ok: true });
  });

  describe("when current locale is en", () => {
    beforeEach(() => {
      mockedUseLocale.mockReturnValue("en");
    });

    it("renders Bulgarian flag (🇧🇬) to indicate switch target", () => {
      render(<LanguageToggle />);
      const button = screen.getByRole("button");
      expect(button).toHaveTextContent("🇧🇬");
    });

    it("has aria-label for switching to Bulgarian", () => {
      render(<LanguageToggle />);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-label", "Превключи на български");
    });

    it("navigates to bg locale on click", () => {
      render(<LanguageToggle />);
      fireEvent.click(screen.getByRole("button"));
      expect(mockReplace).toHaveBeenCalledWith(mockPathname, { locale: "bg" });
    });

    it("sets NEXT_LOCALE cookie to bg on click", () => {
      render(<LanguageToggle />);
      fireEvent.click(screen.getByRole("button"));
      expect(document.cookie).toContain("NEXT_LOCALE=bg");
    });

    it("sends locale preference update to backend on click", () => {
      render(<LanguageToggle />);
      fireEvent.click(screen.getByRole("button"));
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/v1/locale",
        expect.objectContaining({
          method: "PATCH",
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
          body: JSON.stringify({ locale: "bg" }),
          credentials: "include",
        })
      );
    });
  });

  describe("when current locale is bg", () => {
    beforeEach(() => {
      mockedUseLocale.mockReturnValue("bg");
    });

    it("renders English flag (🇬🇧) to indicate switch target", () => {
      render(<LanguageToggle />);
      const button = screen.getByRole("button");
      expect(button).toHaveTextContent("🇬🇧");
    });

    it("has aria-label for switching to English", () => {
      render(<LanguageToggle />);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-label", "Switch to English");
    });

    it("navigates to en locale on click", () => {
      render(<LanguageToggle />);
      fireEvent.click(screen.getByRole("button"));
      expect(mockReplace).toHaveBeenCalledWith(mockPathname, { locale: "en" });
    });

    it("sets NEXT_LOCALE cookie to en on click", () => {
      render(<LanguageToggle />);
      fireEvent.click(screen.getByRole("button"));
      expect(document.cookie).toContain("NEXT_LOCALE=en");
    });
  });

  it("does not crash if backend locale update fails", () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network error")
    );
    mockedUseLocale.mockReturnValue("en");
    render(<LanguageToggle />);

    // Should not throw
    expect(() => {
      fireEvent.click(screen.getByRole("button"));
    }).not.toThrow();
  });

  it("has minimum touch target size (44px)", () => {
    mockedUseLocale.mockReturnValue("en");
    render(<LanguageToggle />);
    const button = screen.getByRole("button");
    expect(button.className).toContain("min-w-[44px]");
    expect(button.className).toContain("min-h-[44px]");
  });
});
