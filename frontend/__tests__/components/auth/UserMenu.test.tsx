import { render, screen, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { UserMenu } from "@/components/auth/UserMenu";

const mockLogout = vi.fn();
const mockUser = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: "https://example.com/avatar.jpg",
  is_admin: false,
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    isAuthenticated: true,
    error: null,
    login: vi.fn(),
    logout: mockLogout,
    loginComplete: vi.fn(),
  }),
}));

describe("UserMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders avatar when avatar_url is present", () => {
    render(<UserMenu />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", mockUser.avatar_url);
  });

  it("renders initial circle when avatar_url is null", () => {
    const originalUrl = mockUser.avatar_url;
    mockUser.avatar_url = null;
    render(<UserMenu />);
    expect(screen.getByText("M")).toBeInTheDocument();
    mockUser.avatar_url = originalUrl;
  });

  it("has aria-expanded and aria-haspopup on trigger", () => {
    render(<UserMenu />);
    const trigger = screen.getByRole("button", { name: /user menu/i });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveAttribute("aria-haspopup", "true");
  });

  it("opens dropdown on click", () => {
    render(<UserMenu />);
    const trigger = screen.getByRole("button", { name: /user menu/i });

    act(() => {
      trigger.click();
    });

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("group", { name: /user menu/i })).toBeInTheDocument();
  });

  it("contains expected links", () => {
    render(<UserMenu />);
    act(() => {
      screen.getByRole("button", { name: /user menu/i }).click();
    });

    expect(screen.getByText("My Account").closest("a")).toHaveAttribute(
      "href",
      "/account"
    );
    expect(screen.getByText("My Orders").closest("a")).toHaveAttribute(
      "href",
      "/orders"
    );
    expect(screen.getByText("Sign Out")).toBeInTheDocument();
  });

  it("calls logout on Sign Out click", async () => {
    render(<UserMenu />);
    act(() => {
      screen.getByRole("button", { name: /user menu/i }).click();
    });

    await act(async () => {
      screen.getByText("Sign Out").click();
    });

    expect(mockLogout).toHaveBeenCalled();
  });

  it("closes on Escape key and returns focus to trigger", () => {
    render(<UserMenu />);
    const trigger = screen.getByRole("button", { name: /user menu/i });

    act(() => {
      trigger.click();
    });
    expect(screen.getByRole("group", { name: /user menu/i })).toBeInTheDocument();

    act(() => {
      const event = new KeyboardEvent("keydown", { key: "Escape" });
      document.dispatchEvent(event);
    });

    expect(screen.queryByRole("group", { name: /user menu/i })).not.toBeInTheDocument();
    expect(document.activeElement).toBe(trigger);
  });

  it("closes on click outside", () => {
    render(<UserMenu />);
    act(() => {
      screen.getByRole("button", { name: /user menu/i }).click();
    });
    expect(screen.getByRole("group", { name: /user menu/i })).toBeInTheDocument();

    act(() => {
      const event = new MouseEvent("mousedown", { bubbles: true });
      document.body.dispatchEvent(event);
    });

    expect(screen.queryByRole("group", { name: /user menu/i })).not.toBeInTheDocument();
  });
});
