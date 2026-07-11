import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect } from "vitest";

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

const mockLogin = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    login: mockLogin,
    logout: vi.fn(),
    loginComplete: vi.fn(),
  }),
}));

import { LoginButton } from "@/components/auth/LoginButton";

describe("LoginButton", () => {
  it("renders 'Sign In' text", () => {
    render(<LoginButton />);
    expect(screen.getByText("signIn")).toBeInTheDocument();
  });

  it("calls login() from useAuth on click", async () => {
    const user = userEvent.setup();
    render(<LoginButton />);

    await user.click(screen.getByText("signIn"));
    expect(mockLogin).toHaveBeenCalled();
  });
});
