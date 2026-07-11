/**
 * Translation rendering spot-check tests.
 *
 * Verifies that key components render correctly in both English and Bulgarian
 * by using the actual message files and next-intl's IntlProvider.
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { NextIntlClientProvider } from "next-intl";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

// Mock contexts
vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({
    items: [],
    total_cents: 0,
    item_count: 0,
    isLoading: false,
    error: null,
    isDrawerOpen: false,
    addToCart: vi.fn(),
    updateQuantity: vi.fn(),
    removeItem: vi.fn(),
    openDrawer: vi.fn(),
    closeDrawer: vi.fn(),
    refreshCart: vi.fn(),
    dismissError: vi.fn(),
  }),
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    loginComplete: vi.fn(),
  }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/products",
}));

vi.mock("@/components/auth/LoginButton", () => ({
  LoginButton: () => <button>Sign In</button>,
}));

vi.mock("@/components/auth/UserMenu", () => ({
  UserMenu: () => <div>UserMenu</div>,
}));

import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

function renderWithLocale(
  ui: React.ReactElement,
  locale: "en" | "bg",
  messages: Record<string, unknown>
) {
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      {ui}
    </NextIntlClientProvider>
  );
}

describe("Header translation rendering", () => {
  it("renders English navigation labels", () => {
    renderWithLocale(<Header />, "en", enMessages);
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Shop")).toBeInTheDocument();
  });

  it("renders Bulgarian navigation labels", () => {
    renderWithLocale(<Header />, "bg", bgMessages);
    expect(screen.getByText("Начало")).toBeInTheDocument();
    expect(screen.getByText("Магазин")).toBeInTheDocument();
  });

  it("renders English cart aria-label when empty", () => {
    renderWithLocale(<Header />, "en", enMessages);
    const cartButton = screen.getByRole("button", { name: /shopping cart/i });
    expect(cartButton).toBeInTheDocument();
  });

  it("renders Bulgarian cart aria-label when empty", () => {
    renderWithLocale(<Header />, "bg", bgMessages);
    const cartButton = screen.getByRole("button", { name: /кошница/i });
    expect(cartButton).toBeInTheDocument();
  });
});

describe("Footer translation rendering", () => {
  it("renders English footer text", () => {
    renderWithLocale(<Footer />, "en", enMessages);
    expect(screen.getByText("Handcrafted with love")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Shop")).toBeInTheDocument();
    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("Contact")).toBeInTheDocument();
  });

  it("renders Bulgarian footer text", () => {
    renderWithLocale(<Footer />, "bg", bgMessages);
    expect(screen.getByText("Ръчна изработка с любов")).toBeInTheDocument();
    expect(screen.getByText("Начало")).toBeInTheDocument();
    expect(screen.getByText("Магазин")).toBeInTheDocument();
    expect(screen.getByText("За нас")).toBeInTheDocument();
    expect(screen.getByText("Контакт")).toBeInTheDocument();
  });

  it("renders copyright with current year in English", () => {
    renderWithLocale(<Footer />, "en", enMessages);
    const year = new Date().getFullYear();
    expect(
      screen.getByText(`© ${year} Atelier Marie. All rights reserved.`)
    ).toBeInTheDocument();
  });

  it("renders copyright with current year in Bulgarian", () => {
    renderWithLocale(<Footer />, "bg", bgMessages);
    const year = new Date().getFullYear();
    expect(
      screen.getByText(`© ${year} Ателие Мари. Всички права запазени.`)
    ).toBeInTheDocument();
  });
});

describe("Message file completeness", () => {
  it("bg.json has all top-level namespaces from en.json", () => {
    const enNamespaces = Object.keys(enMessages);
    const bgNamespaces = Object.keys(bgMessages);
    for (const ns of enNamespaces) {
      expect(bgNamespaces).toContain(ns);
    }
  });

  it("bg.json has all keys within each namespace", () => {
    for (const [ns, enSection] of Object.entries(enMessages)) {
      const bgSection = (bgMessages as Record<string, Record<string, string>>)[
        ns
      ];
      expect(bgSection).toBeDefined();
      for (const key of Object.keys(
        enSection as Record<string, string>
      )) {
        expect(bgSection).toHaveProperty(
          key,
          expect.anything()
        );
      }
    }
  });

  it("locale namespace has switchToEnglish and switchToBulgarian", () => {
    expect(enMessages.locale.switchToEnglish).toBeDefined();
    expect(enMessages.locale.switchToBulgarian).toBeDefined();
    expect(bgMessages.locale.switchToEnglish).toBeDefined();
    expect(bgMessages.locale.switchToBulgarian).toBeDefined();
  });
});
