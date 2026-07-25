/**
 * Translation rendering spot-check tests.
 *
 * Verifies that key components render correctly in both English and Bulgarian
 * by using the actual message files and next-intl's IntlProvider.
 */
import { render, screen, fireEvent } from "@testing-library/react";
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

vi.mock("@/lib/api", () => ({
  submitContact: vi.fn(),
}));

import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ContactForm } from "@/components/contact/ContactForm";

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
    expect(screen.getByLabelText("Follow Atelier Marie on Instagram")).toHaveAttribute(
      "href",
      "https://www.instagram.com/atelier_marie25?igsh=MWQ1YzA4aHF2a3Q4MA=="
    );
    expect(screen.getByLabelText("Follow Atelier Marie on TikTok")).toHaveAttribute(
      "href",
      "https://www.tiktok.com/@ateliermarie25?_r=1&_t=ZN-98H9buODbdu"
    );
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

  it("locale namespace has changeLanguage in both locales", () => {
    expect(enMessages.locale.changeLanguage).toBeDefined();
    expect(bgMessages.locale.changeLanguage).toBeDefined();
  });
});

describe("ContactForm translation rendering", () => {
  it("renders English field labels and submit button", () => {
    renderWithLocale(<ContactForm />, "en", enMessages);
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument();
  });

  it("renders Bulgarian field labels and submit button", () => {
    renderWithLocale(<ContactForm />, "bg", bgMessages);
    // Use exact label text (accessible name includes the trailing " *" from the required span)
    expect(screen.getByLabelText("Име *")).toBeInTheDocument();
    expect(screen.getByLabelText("Имейл *")).toBeInTheDocument();
    expect(screen.getByLabelText("Съобщение *")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /изпрати съобщение/i })).toBeInTheDocument();
  });

  it("renders Bulgarian validation errors", async () => {
    renderWithLocale(<ContactForm />, "bg", bgMessages);
    fireEvent.click(screen.getByRole("button", { name: /изпрати съобщение/i }));
    expect(await screen.findByText("Името е задължително")).toBeInTheDocument();
    expect(screen.getByText("Имейлът е задължителен")).toBeInTheDocument();
    expect(screen.getByText("Съобщението е задължително")).toBeInTheDocument();
  });
});
