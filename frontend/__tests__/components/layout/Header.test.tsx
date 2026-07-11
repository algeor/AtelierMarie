import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { Header } from "@/components/layout/Header";

let mockAuthState = {
  user: null as { id: string; email: string; name: string | null; avatar_url: string | null; is_admin: boolean } | null,
  isLoading: false,
  isAuthenticated: false,
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
  loginComplete: vi.fn(),
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuthState,
}));

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

describe("Header", () => {
  beforeEach(() => {
    mockAuthState = {
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
      login: vi.fn(),
      logout: vi.fn(),
      loginComplete: vi.fn(),
    };
  });

  it("shows LoginButton when not authenticated", () => {
    render(<Header />);
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("shows UserMenu when authenticated", () => {
    mockAuthState.user = {
      id: "user-001",
      email: "marie@ateliermarie.com",
      name: "Marie",
      avatar_url: "https://example.com/avatar.jpg",
      is_admin: false,
    };
    mockAuthState.isAuthenticated = true;

    render(<Header />);
    expect(screen.getByRole("button", { name: /user menu/i })).toBeInTheDocument();
    expect(screen.queryByText("Sign In")).not.toBeInTheDocument();
  });

  it("shows skeleton circle while isLoading", () => {
    mockAuthState.isLoading = true;
    render(<Header />);
    const skeleton = document.querySelector("[aria-hidden='true']");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass("rounded-full");
  });
});
