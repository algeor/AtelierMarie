import { screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import type { UserResponse } from "@/lib/types";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

const mockReplace = vi.fn();
const mockLoginComplete = vi.fn();
const mockLogin = vi.fn();

let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    login: mockLogin,
    logout: vi.fn(),
    loginComplete: mockLoginComplete,
  }),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
}));

vi.mock("@/lib/validateRedirectPath", () => ({
  validateRedirectPath: (path: string) => (path.startsWith("/") && !path.startsWith("//") ? path : "/"),
}));

import { getCurrentUser } from "@/lib/api";
import { CallbackHandler } from "@/app/[locale]/auth/callback/CallbackHandler";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);

const mockUser: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: null,
  is_admin: false,
};

describe("CallbackHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    sessionStorage.clear();
  });

  it("calls getCurrentUser and navigates on success", async () => {
    mockSearchParams = new URLSearchParams("success=true&redirect_to=/products");
    mockedGetCurrentUser.mockResolvedValueOnce(mockUser);

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(mockLoginComplete).toHaveBeenCalledWith(mockUser);
    });
    expect(mockReplace).toHaveBeenCalledWith("/products");
  });

  it("shows error immediately when error param is present", async () => {
    mockSearchParams = new URLSearchParams("error=invalid_state");

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(screen.getByText(/Sign in failed/)).toBeInTheDocument();
    });
    // Should NOT call getCurrentUser
    expect(mockedGetCurrentUser).not.toHaveBeenCalled();
  });

  it("shows error when getCurrentUser returns null", async () => {
    mockSearchParams = new URLSearchParams("success=true");
    mockedGetCurrentUser.mockResolvedValueOnce(null);

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(screen.getByText(/Sign in failed/)).toBeInTheDocument();
    });
  });

  it("shows error when getCurrentUser throws", async () => {
    mockSearchParams = new URLSearchParams("success=true");
    mockedGetCurrentUser.mockRejectedValueOnce(new Error("Network error"));

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(screen.getByText(/Sign in failed/)).toBeInTheDocument();
    });
  });

  it("uses sessionStorage fallback for redirect", async () => {
    mockSearchParams = new URLSearchParams("success=true");
    sessionStorage.setItem("auth_redirect_to", "/account");
    mockedGetCurrentUser.mockResolvedValueOnce(mockUser);

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/account");
    });
  });

  it("clears sessionStorage after reading", async () => {
    mockSearchParams = new URLSearchParams("success=true&redirect_to=/orders");
    sessionStorage.setItem("auth_redirect_to", "/account");
    mockedGetCurrentUser.mockResolvedValueOnce(mockUser);

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalled();
    });
    expect(sessionStorage.getItem("auth_redirect_to")).toBeNull();
  });

  it("validates redirect_to path", async () => {
    mockSearchParams = new URLSearchParams("success=true&redirect_to=//evil.com");
    mockedGetCurrentUser.mockResolvedValueOnce(mockUser);

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("shows loading state initially", () => {
    mockedGetCurrentUser.mockReturnValue(new Promise(() => {})); // never resolves
    mockSearchParams = new URLSearchParams("success=true");

    renderWithIntl(<CallbackHandler />);
    expect(screen.getByText("Signing you in...")).toBeInTheDocument();
  });

  it("shows retry button on error that calls login", async () => {
    const userEvent = (await import("@testing-library/user-event")).default;
    const user = userEvent.setup();
    mockSearchParams = new URLSearchParams("error=token_exchange_failed");

    renderWithIntl(<CallbackHandler />);

    await waitFor(() => {
      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Try Again"));
    expect(mockLogin).toHaveBeenCalled();
  });
});
