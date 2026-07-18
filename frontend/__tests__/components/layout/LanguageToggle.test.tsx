/**
 * Tests for LanguageToggle dropdown.
 *
 * Verifies:
 * - Trigger shows flag of the CURRENT locale (not the target)
 * - Dropdown closed by default; opens on trigger click
 * - Selecting a different locale navigates, sets the cookie, calls the backend
 * - Selecting the active locale is a no-op (menu just closes)
 * - Escape and click-outside close the menu
 * - 44px touch target and graceful backend failure preserved
 */
import { render, screen, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockReplace = vi.fn();
const mockPathname = "/products";

vi.mock("next-intl", () => ({
  useLocale: vi.fn(() => "en"),
  useTranslations: vi.fn(() => (key: string) => {
    const translations: Record<string, string> = {
      changeLanguage: "Change language",
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

function openMenu() {
  fireEvent.click(screen.getByRole("button", { name: /change language/i }));
}

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

  describe("trigger shows the CURRENT locale's flag", () => {
    it("shows the English flag (🇬🇧) and EN code when locale is en", () => {
      mockedUseLocale.mockReturnValue("en");
      render(<LanguageToggle />);
      const trigger = screen.getByRole("button", { name: /change language/i });
      expect(trigger).toHaveTextContent("🇬🇧");
      expect(trigger).toHaveTextContent("EN");
    });

    it("shows the Bulgarian flag (🇧🇬) and BG code when locale is bg", () => {
      mockedUseLocale.mockReturnValue("bg");
      render(<LanguageToggle />);
      const trigger = screen.getByRole("button", { name: /change language/i });
      expect(trigger).toHaveTextContent("🇧🇬");
      expect(trigger).toHaveTextContent("BG");
    });
  });

  describe("dropdown visibility", () => {
    it("is closed by default (aria-expanded=false, no menu in DOM)", () => {
      mockedUseLocale.mockReturnValue("en");
      render(<LanguageToggle />);
      const trigger = screen.getByRole("button", { name: /change language/i });
      expect(trigger).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("opens when the trigger is clicked", () => {
      mockedUseLocale.mockReturnValue("en");
      render(<LanguageToggle />);
      openMenu();
      const trigger = screen.getByRole("button", { name: /change language/i });
      expect(trigger).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByRole("menu")).toBeInTheDocument();
      expect(
        screen.getByRole("menuitem", { name: /switch to english/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("menuitem", { name: /превключи на български/i })
      ).toBeInTheDocument();
    });

    it("marks the active locale with aria-current when open (en active)", () => {
      mockedUseLocale.mockReturnValue("en");
      render(<LanguageToggle />);
      openMenu();
      const enItem = screen.getByRole("menuitem", { name: /switch to english/i });
      const bgItem = screen.getByRole("menuitem", {
        name: /превключи на български/i,
      });
      expect(enItem).toHaveAttribute("aria-current", "true");
      expect(bgItem).not.toHaveAttribute("aria-current");
    });

    it("marks the active locale with aria-current when open (bg active)", () => {
      mockedUseLocale.mockReturnValue("bg");
      render(<LanguageToggle />);
      openMenu();
      const enItem = screen.getByRole("menuitem", { name: /switch to english/i });
      const bgItem = screen.getByRole("menuitem", {
        name: /превключи на български/i,
      });
      expect(bgItem).toHaveAttribute("aria-current", "true");
      expect(enItem).not.toHaveAttribute("aria-current");
    });
  });

  describe("selecting the other locale", () => {
    beforeEach(() => {
      mockedUseLocale.mockReturnValue("en");
    });

    it("navigates to the selected locale", () => {
      render(<LanguageToggle />);
      openMenu();
      fireEvent.click(
        screen.getByRole("menuitem", { name: /превключи на български/i })
      );
      expect(mockReplace).toHaveBeenCalledWith(mockPathname, { locale: "bg" });
    });

    it("sets the NEXT_LOCALE cookie", () => {
      render(<LanguageToggle />);
      openMenu();
      fireEvent.click(
        screen.getByRole("menuitem", { name: /превключи на български/i })
      );
      expect(document.cookie).toContain("NEXT_LOCALE=bg");
    });

    it("sends locale preference update to the backend", () => {
      render(<LanguageToggle />);
      openMenu();
      fireEvent.click(
        screen.getByRole("menuitem", { name: /превключи на български/i })
      );
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

    it("closes the menu after selection", () => {
      render(<LanguageToggle />);
      openMenu();
      fireEvent.click(
        screen.getByRole("menuitem", { name: /превключи на български/i })
      );
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  describe("selecting the active locale", () => {
    it("does not navigate and does not touch cookie/backend", () => {
      mockedUseLocale.mockReturnValue("en");
      render(<LanguageToggle />);
      openMenu();
      fireEvent.click(
        screen.getByRole("menuitem", { name: /switch to english/i })
      );
      expect(mockReplace).not.toHaveBeenCalled();
      expect(document.cookie).not.toContain("NEXT_LOCALE=");
      expect(global.fetch).not.toHaveBeenCalled();
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  describe("dismissing the menu", () => {
    it("closes on Escape and returns focus to the trigger", () => {
      mockedUseLocale.mockReturnValue("en");
      render(<LanguageToggle />);
      openMenu();
      expect(screen.getByRole("menu")).toBeInTheDocument();

      act(() => {
        fireEvent.keyDown(document, { key: "Escape" });
      });

      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /change language/i })
      ).toHaveFocus();
    });

    it("closes on click outside", () => {
      mockedUseLocale.mockReturnValue("en");
      render(
        <div>
          <LanguageToggle />
          <button data-testid="outside">Outside</button>
        </div>
      );
      openMenu();
      expect(screen.getByRole("menu")).toBeInTheDocument();

      fireEvent.mouseDown(screen.getByTestId("outside"));

      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  it("does not crash if the backend locale update fails", () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("Network error")
    );
    mockedUseLocale.mockReturnValue("en");
    render(<LanguageToggle />);
    openMenu();

    expect(() => {
      fireEvent.click(
        screen.getByRole("menuitem", { name: /превключи на български/i })
      );
    }).not.toThrow();
  });

  it("trigger has minimum touch target size (44px)", () => {
    mockedUseLocale.mockReturnValue("en");
    render(<LanguageToggle />);
    const trigger = screen.getByRole("button", { name: /change language/i });
    expect(trigger.className).toContain("min-w-[44px]");
    expect(trigger.className).toContain("min-h-[44px]");
  });
});
