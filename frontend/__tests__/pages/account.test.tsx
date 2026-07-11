import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import AccountPage from "@/app/account/page";

const mockLogin = vi.fn();
const mockLogout = vi.fn();

let mockAuthState = {
  user: null as { id: string; email: string; name: string | null; avatar_url: string | null; is_admin: boolean } | null,
  isLoading: false,
  isAuthenticated: false,
  error: null,
  login: mockLogin,
  logout: mockLogout,
  loginComplete: vi.fn(),
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuthState,
}));

describe("AccountPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthState = {
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
      login: mockLogin,
      logout: mockLogout,
      loginComplete: vi.fn(),
    };
  });

  it("shows loading skeleton when isLoading is true", () => {
    mockAuthState.isLoading = true;
    render(<AccountPage />);
    const skeletons = document.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows anonymous view with Sign In button", () => {
    render(<AccountPage />);
    expect(
      screen.getByText("Sign in to view your account and order history")
    ).toBeInTheDocument();
    expect(screen.getByText("Sign In with Google")).toBeInTheDocument();
  });

  it("Sign In with Google button triggers login", () => {
    render(<AccountPage />);
    screen.getByText("Sign In with Google").click();
    expect(mockLogin).toHaveBeenCalled();
  });

  it("shows authenticated view with user info", () => {
    mockAuthState.user = {
      id: "user-001",
      email: "marie@ateliermarie.com",
      name: "Marie",
      avatar_url: "https://example.com/avatar.jpg",
      is_admin: false,
    };
    mockAuthState.isAuthenticated = true;

    render(<AccountPage />);
    expect(screen.getByText("Marie")).toBeInTheDocument();
    expect(screen.getByText("marie@ateliermarie.com")).toBeInTheDocument();
    // Avatar rendered via next/image (alt includes user name, so role="img")
    const img = screen.getByRole("img", { name: /marie avatar/i });
    expect(img).toHaveAttribute(
      "src",
      expect.stringContaining(encodeURIComponent("https://example.com/avatar.jpg"))
    );
    expect(screen.getByText("My Orders")).toBeInTheDocument();
    expect(screen.getByText("Sign Out")).toBeInTheDocument();
  });

  it("Sign Out button triggers logout", () => {
    mockAuthState.user = {
      id: "user-001",
      email: "marie@ateliermarie.com",
      name: "Marie",
      avatar_url: null,
      is_admin: false,
    };
    mockAuthState.isAuthenticated = true;

    render(<AccountPage />);
    screen.getByText("Sign Out").click();
    expect(mockLogout).toHaveBeenCalled();
  });
});
