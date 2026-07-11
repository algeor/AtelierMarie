import { render, screen, waitFor, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
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

import { getCurrentUser, logout } from "@/lib/api";
import { validateRedirectPath } from "@/lib/validateRedirectPath";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedLogout = vi.mocked(logout);
const mockedValidateRedirectPath = vi.mocked(validateRedirectPath);

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

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    // Mock window.location
    Object.defineProperty(window, "location", {
      value: { pathname: "/products", href: "" },
      writable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("hydration", () => {
    it("hydrates with authenticated user", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      renderWithProvider();

      expect(screen.getByTestId("loading")).toHaveTextContent("true");

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });
      expect(screen.getByTestId("user")).toHaveTextContent("Marie");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    it("hydrates as anonymous when getCurrentUser returns null", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });
      expect(screen.getByTestId("user")).toHaveTextContent("null");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    it("handles network failure during hydration", async () => {
      mockedGetCurrentUser.mockRejectedValueOnce(new Error("Network error"));
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });
      expect(screen.getByTestId("user")).toHaveTextContent("null");
      expect(screen.getByTestId("error")).toHaveTextContent(
        "Failed to check authentication status."
      );
    });

    it("uses cancelled flag to prevent stale dispatches", async () => {
      let resolvePromise: (value: UserResponse | null) => void;
      mockedGetCurrentUser.mockReturnValueOnce(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const { unmount } = renderWithProvider();
      unmount();

      // Resolve after unmount — should not throw
      await act(async () => {
        resolvePromise!(mockUser);
      });
    });
  });

  describe("login", () => {
    it("validates redirect path and navigates to OAuth URL", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      mockedValidateRedirectPath.mockReturnValueOnce("/products");

      renderWithProvider();
      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });

      const sessionSetItem = vi.spyOn(Storage.prototype, "setItem");

      act(() => {
        screen.getByText("login").click();
      });

      expect(mockedValidateRedirectPath).toHaveBeenCalledWith("/products");
      expect(sessionSetItem).toHaveBeenCalledWith(
        "auth_redirect_to",
        "/products"
      );
      expect(window.location.href).toContain("/v1/auth/login?redirect_to=");

      sessionSetItem.mockRestore();
    });
  });

  describe("logout", () => {
    it("clears state on successful logout", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      mockedLogout.mockResolvedValueOnce(undefined);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
      });

      await act(async () => {
        screen.getByText("logout").click();
      });

      expect(screen.getByTestId("user")).toHaveTextContent("null");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    });

    it("still clears state when logout API call fails", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      mockedLogout.mockRejectedValueOnce(new Error("Network error"));
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      renderWithProvider();
      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
      });

      await act(async () => {
        screen.getByText("logout").click();
      });

      expect(screen.getByTestId("user")).toHaveTextContent("null");
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe("loginComplete", () => {
    it("updates state with user object", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("false");
      });

      act(() => {
        screen.getByText("loginComplete").click();
      });

      expect(screen.getByTestId("user")).toHaveTextContent("Marie");
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });
  });

  describe("session-rotated event", () => {
    it("re-fetches user on session-rotated event", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
      });

      mockedGetCurrentUser.mockResolvedValueOnce(null);

      await act(async () => {
        window.dispatchEvent(new Event("session-rotated"));
      });

      await waitFor(() => {
        expect(screen.getByTestId("user")).toHaveTextContent("null");
      });
    });
  });

  describe("error auto-clear", () => {
    it("clears error after 5 seconds", async () => {
      mockedGetCurrentUser.mockRejectedValueOnce(new Error("fail"));
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("error")).toHaveTextContent(
          "Failed to check authentication status."
        );
      });

      act(() => {
        vi.advanceTimersByTime(5000);
      });

      expect(screen.getByTestId("error")).toHaveTextContent("");
    });
  });

  describe("isAuthenticated derivation", () => {
    it("is true when user is present", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(mockUser);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
      });
    });

    it("is false when user is null", async () => {
      mockedGetCurrentUser.mockResolvedValueOnce(null);
      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
      });
    });
  });

  describe("useAuth outside provider", () => {
    it("throws when used outside AuthProvider", () => {
      const spy = vi.spyOn(console, "error").mockImplementation(() => {});
      expect(() => render(<TestComponent />)).toThrow(
        "useAuth must be used within an AuthProvider"
      );
      spy.mockRestore();
    });
  });
});
