import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockLogin = vi.fn();

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (values) {
      return Object.entries(values).reduce(
        (str, [k, v]) => str.replace(`{${k}}`, String(v)),
        key
      );
    }
    return key;
  },
  useLocale: () => "en",
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@/contexts/AuthContext";
import AccountPage from "@/app/[locale]/account/page";

const mockedUseAuth = vi.mocked(useAuth);

describe("AccountPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("authenticated view", () => {
    beforeEach(() => {
      mockedUseAuth.mockReturnValue({
        user: {
          id: "user-001",
          email: "marie@ateliermarie.com",
          name: "Marie",
          avatar_url: "https://example.com/avatar.jpg",
          is_admin: false,
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: mockLogin,
        logout: vi.fn(),
        loginComplete: vi.fn(),
      });
    });

    it("shows user name and email", () => {
      render(<AccountPage />);
      expect(screen.getByText("Marie")).toBeInTheDocument();
      expect(screen.getByText("marie@ateliermarie.com")).toBeInTheDocument();
    });

    it("shows avatar image", () => {
      render(<AccountPage />);
      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("src", "https://example.com/avatar.jpg");
    });

    it("shows My Orders link", () => {
      render(<AccountPage />);
      expect(screen.getByText("My Orders")).toHaveAttribute("href", "/orders");
    });
  });

  describe("anonymous view", () => {
    beforeEach(() => {
      mockedUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        login: mockLogin,
        logout: vi.fn(),
        loginComplete: vi.fn(),
      });
    });

    it("shows sign in prompt", () => {
      render(<AccountPage />);
      expect(
        screen.getByText("Sign in to view your account and order history")
      ).toBeInTheDocument();
    });

    it("shows Sign In with Google button that calls login", async () => {
      const user = userEvent.setup();
      render(<AccountPage />);

      const button = screen.getByText("Sign In with Google");
      await user.click(button);
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  describe("loading state", () => {
    it("shows skeleton while loading", () => {
      mockedUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: true,
        error: null,
        login: mockLogin,
        logout: vi.fn(),
        loginComplete: vi.fn(),
      });

      render(<AccountPage />);
      // Should not show the sign-in prompt or user info
      expect(screen.queryByText("Sign In with Google")).not.toBeInTheDocument();
      expect(screen.queryByText("marie@ateliermarie.com")).not.toBeInTheDocument();
    });
  });
});
