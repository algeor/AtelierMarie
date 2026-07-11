import { Component, type ReactNode } from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import type { UserResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("@/lib/validateRedirectPath", () => ({
  validateRedirectPath: vi.fn((path: string) =>
    path.startsWith("/") && !path.startsWith("//") ? path : "/"
  ),
}));

import { getCurrentUser, logout as apiLogout } from "@/lib/api";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedApiLogout = vi.mocked(apiLogout);

const mockUser: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: "https://example.com/avatar.jpg",
  is_admin: false,
};

function TestComponent() {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="user">{auth.user?.name ?? "null"}</div>
      <div data-testid="loading">{String(auth.isLoading)}</div>
      <div data-testid="authenticated">{String(auth.isAuthenticated)}</div>
      <div data-testid="error">{auth.error ?? ""}</div>
      <button onClick={auth.login}>login</button>
      <button onClick={auth.logout}>logout</button>
      <button onClick={() => auth.loginComplete(mockUser)}>loginComplete</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );
}

class AuthErrorBoundary extends Component<
  { children: ReactNode },
  { message: string | null }
> {
  state = { message: null };

  static getDerivedStateFromError(error: Error) {
    return { message: error.message };
  }

  render() {
    if (this.state.message) {
      return <div data-testid="auth-error">{this.state.message}</div>;
    }
    return this.props.children;
  }
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("hydration", () => {
    it("hydrates with authenticated user", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      renderWithProvider();

      expect(screen.getByTestId("loading").textContent).toBe("true");

      await waitFor(() => {
        expect(screen.getByTestId("loading").textContent).toBe("false");
      });
      expect(screen.getByTestId("user").textContent).toBe("Marie");
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });

    it("hydrates as anonymous when getCurrentUser returns null", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("loading").textContent).toBe("false");
      });
      expect(screen.getByTestId("user").textContent).toBe("null");
      expect(screen.getByTestId("authenticated").textContent).toBe("false");
    });

    it("handles hydration network failure", async () => {
      mockedGetCurrentUser.mockRejectedValueOnce(new Error("Network error"));
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("loading").textContent).toBe("false");
      });
      expect(screen.getByTestId("user").textContent).toBe("null");
      expect(screen.getByTestId("error").textContent).toBe(
        "Failed to check authentication status."
      );
    });
  });

  describe("login", () => {
    it("navigates to backend auth login URL", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);

      // Mock window.location
      const originalLocation = window.location;
      Object.defineProperty(window, "location", {
        value: { pathname: "/products", search: "", href: "" },
        writable: true,
        configurable: true,
      });

      renderWithProvider();
      await waitFor(() => {
        expect(screen.getByTestId("loading").textContent).toBe("false");
      });

      act(() => {
        screen.getByText("login").click();
      });

      expect(window.location.href).toContain("/v1/auth/login?redirect_to=");

      Object.defineProperty(window, "location", {
        value: originalLocation,
        writable: true,
        configurable: true,
      });
    });
  });

  describe("logout", () => {
    it("clears user state on successful logout", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      mockedApiLogout.mockResolvedValueOnce(undefined);

      renderWithProvider();
      await waitFor(() => {
        expect(screen.getByTestId("authenticated").textContent).toBe("true");
      });

      await act(async () => {
        screen.getByText("logout").click();
      });

      expect(screen.getByTestId("user").textContent).toBe("null");
      expect(screen.getByTestId("authenticated").textContent).toBe("false");
    });

    it("clears user state even when API call fails", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      mockedApiLogout.mockRejectedValueOnce(new Error("Network error"));

      renderWithProvider();
      await waitFor(() => {
        expect(screen.getByTestId("authenticated").textContent).toBe("true");
      });

      await act(async () => {
        screen.getByText("logout").click();
      });

      // User intent is to log out regardless of server response
      expect(screen.getByTestId("user").textContent).toBe("null");
      expect(screen.getByTestId("authenticated").textContent).toBe("false");
    });
  });

  describe("loginComplete", () => {
    it("updates state with user object", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("loading").textContent).toBe("false");
      });

      act(() => {
        screen.getByText("loginComplete").click();
      });

      expect(screen.getByTestId("user").textContent).toBe("Marie");
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });
  });

  describe("session-rotated event", () => {
    it("re-fetches user on session-rotated event", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated").textContent).toBe("true");
      });

      // Simulate session rotation — user logged out
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      act(() => {
        window.dispatchEvent(new Event("session-rotated"));
      });

      await waitFor(() => {
        expect(screen.getByTestId("user").textContent).toBe("null");
      });
    });
  });

  describe("error auto-clear", () => {
    it("clears error after 5 seconds", async () => {
      vi.useFakeTimers();
      mockedGetCurrentUser.mockRejectedValueOnce(new Error("fail"));

      renderWithProvider();

      // Advance to let the promise microtask run
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(screen.getByTestId("error").textContent).toBe(
        "Failed to check authentication status."
      );

      act(() => {
        vi.advanceTimersByTime(5000);
      });

      expect(screen.getByTestId("error").textContent).toBe("");
      vi.useRealTimers();
    });
  });

  describe("isAuthenticated derivation", () => {
    it("is true when user is non-null", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated").textContent).toBe("true");
      });
    });

    it("is false when user is null", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated").textContent).toBe("false");
      });
    });
  });

  describe("useAuth outside provider", () => {
    it("throws when used outside AuthProvider", () => {
      function Orphan() {
        useAuth();
        return null;
      }

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      const handleWindowError = (event: ErrorEvent) => event.preventDefault();
      window.addEventListener("error", handleWindowError);
      try {
        render(
          <AuthErrorBoundary>
            <Orphan />
          </AuthErrorBoundary>
        );
        expect(screen.getByTestId("auth-error")).toHaveTextContent(
          "useAuth must be used within an AuthProvider"
        );
      } finally {
        window.removeEventListener("error", handleWindowError);
        consoleSpy.mockRestore();
      }
    });
  });
});
