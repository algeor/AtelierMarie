import React from "react";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    children,
    href,
    onClick,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a
      href={href}
      onClick={(event) => {
        event.preventDefault();
        onClick?.(event);
      }}
      {...props}
    >
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/components/layout/LanguageToggle", () => ({
  LanguageToggle: () => <button data-testid="language-toggle">EN</button>,
}));

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({
    items: [],
    unavailable_items: [],
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
  useAuth: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/components/auth/LoginButton", () => ({
  LoginButton: () => <button data-testid="login-button">Sign In</button>,
}));

vi.mock("@/components/auth/UserMenu", () => ({
  UserMenu: () => <div data-testid="user-menu">UserMenu</div>,
}));

import { useAuth } from "@/contexts/AuthContext";
import { Header } from "@/components/layout/Header";

const mockedUseAuth = vi.mocked(useAuth);

function mockAnonymousAuth() {
  mockedUseAuth.mockReturnValue({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    loginComplete: vi.fn(),
  });
}

describe("Header", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows LoginButton when not authenticated", () => {
    mockAnonymousAuth();

    renderWithIntl(<Header />);
    expect(screen.getByTestId("login-button")).toBeInTheDocument();
    expect(screen.queryByTestId("user-menu")).not.toBeInTheDocument();
  });

  it("shows UserMenu when authenticated", () => {
    mockedUseAuth.mockReturnValue({
      user: {
        id: "user-001",
        email: "marie@ateliermarie.com",
        name: "Marie",
        avatar_url: null,
        is_admin: false,
      },
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      loginComplete: vi.fn(),
    });

    renderWithIntl(<Header />);
    expect(screen.getByTestId("user-menu")).toBeInTheDocument();
    expect(screen.queryByTestId("login-button")).not.toBeInTheDocument();
  });

  it("shows skeleton circle while isLoading", () => {
    mockedUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      loginComplete: vi.fn(),
    });

    renderWithIntl(<Header />);
    expect(screen.queryByTestId("login-button")).not.toBeInTheDocument();
    expect(screen.queryByTestId("user-menu")).not.toBeInTheDocument();
    // Skeleton is rendered (aria-hidden div)
    const skeleton = document.querySelector("[aria-hidden='true']");
    expect(skeleton).toBeInTheDocument();
  });

  it("opens a mobile navigation menu with shopper links and account controls", async () => {
    mockAnonymousAuth();
    const user = userEvent.setup();

    renderWithIntl(<Header />);
    await user.click(screen.getByRole("button", { name: "Open menu" }));

    const dialog = await screen.findByRole("dialog", { name: "Menu" });
    expect(within(dialog).getByRole("link", { name: "Shop" })).toHaveAttribute("href", "/products");
    expect(within(dialog).getByRole("link", { name: "Atelier" })).toHaveAttribute("href", "/atelier");
    expect(within(dialog).getByRole("link", { name: "FAQ" })).toHaveAttribute("href", "/faq");
    expect(within(dialog).getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact");
    expect(within(dialog).getByTestId("language-toggle")).toBeInTheDocument();
    expect(within(dialog).getByTestId("login-button")).toBeInTheDocument();
  });

  it("closes the mobile navigation menu after choosing a link", async () => {
    mockAnonymousAuth();
    const user = userEvent.setup();

    renderWithIntl(<Header />);
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    const dialog = await screen.findByRole("dialog", { name: "Menu" });

    await user.click(within(dialog).getByRole("link", { name: "Shop" }));

    expect(screen.queryByRole("dialog", { name: "Menu" })).not.toBeInTheDocument();
  });
});
