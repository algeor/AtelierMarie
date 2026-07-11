import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockReplace = vi.fn();
const mockLogin = vi.fn();
const mockLoginComplete = vi.fn();

let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
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
  validateRedirectPath: vi.fn((path: string) =>
    path.startsWith("/") && !path.startsWith("//") ? path : "/"
  ),
}));

import { getCurrentUser } from "@/lib/api";
import AuthCallbackPage from "@/app/auth/callback/page";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);

const mockUser = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: null,
  is_admin: false,
};

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
    vi.spyOn(Storage.prototype, "getItem").mockReturnValue(null);
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {});
  });

  it("shows loading state", () => {
    mockedGetCurrentUser.mockReturnValue(new Promise(() => {}));
    mockSearchParams = new URLSearchParams("success=true");
    render(<AuthCallbackPage />);
    expect(screen.getByText("Signing you in...")).toBeInTheDocument();
  });

  it("on success, calls loginComplete and navigates to redirect_to", async () => {
    mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
    mockSearchParams = new URLSearchParams("success=true&redirect_to=/products");

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockLoginComplete).toHaveBeenCalledWith(mockUser);
    });
    expect(mockReplace).toHaveBeenCalledWith("/products");
  });

  it("shows error immediately when error param is present", async () => {
    mockSearchParams = new URLSearchParams("error=invalid_state");
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Sign in failed. Please try again.")
      ).toBeInTheDocument();
    });
    expect(mockedGetCurrentUser).not.toHaveBeenCalled();
  });

  it("shows error when getCurrentUser returns null", async () => {
    mockedGetCurrentUser.mockResolvedValueOnce(null);
    mockSearchParams = new URLSearchParams("success=true");
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Sign in failed. Please try again.")
      ).toBeInTheDocument();
    });
  });

  it("shows error when getCurrentUser throws", async () => {
    mockedGetCurrentUser.mockRejectedValueOnce(new Error("Network error"));
    mockSearchParams = new URLSearchParams("success=true");
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Sign in failed. Please try again.")
      ).toBeInTheDocument();
    });
  });

  it("falls back to sessionStorage redirect_to", async () => {
    mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
    mockSearchParams = new URLSearchParams("success=true");
    vi.spyOn(Storage.prototype, "getItem").mockReturnValue("/account");

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/account");
    });
    expect(Storage.prototype.removeItem).toHaveBeenCalledWith("auth_redirect_to");
  });

  it("error state shows Try Again button that triggers login", async () => {
    mockSearchParams = new URLSearchParams("error=failed");
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    screen.getByText("Try Again").click();
    expect(mockLogin).toHaveBeenCalled();
  });
});
