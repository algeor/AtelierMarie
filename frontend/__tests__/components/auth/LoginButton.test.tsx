import React from "react";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect } from "vitest";
import { renderWithIntl } from "../../test-utils";

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
    renderWithIntl(<LoginButton />);
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("calls login() from useAuth on click", async () => {
    const user = userEvent.setup();
    renderWithIntl(<LoginButton />);

    await user.click(screen.getByText("Sign In"));
    expect(mockLogin).toHaveBeenCalled();
  });
});
