import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { LoginButton } from "@/components/auth/LoginButton";

const mockLogin = vi.fn();

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    error: null,
    login: mockLogin,
    logout: vi.fn(),
    loginComplete: vi.fn(),
  }),
}));

describe("LoginButton", () => {
  it("renders 'Sign In' text", () => {
    render(<LoginButton />);
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("calls login() on click", () => {
    render(<LoginButton />);
    screen.getByText("Sign In").click();
    expect(mockLogin).toHaveBeenCalled();
  });
});
