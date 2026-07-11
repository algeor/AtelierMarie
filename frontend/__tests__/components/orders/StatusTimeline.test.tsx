import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { renderWithIntl } from "../../test-utils";

describe("StatusTimeline", () => {
  it("shows 1 filled step for pending", () => {
    renderWithIntl(<StatusTimeline currentStatus="pending" />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    expect(screen.getByText("Shipped")).toBeInTheDocument();
    expect(screen.getByText("Delivered")).toBeInTheDocument();
  });

  it("shows 2 filled steps for confirmed", () => {
    renderWithIntl(<StatusTimeline currentStatus="confirmed" />);
    const pending = screen.getByText("Pending");
    const confirmed = screen.getByText("Confirmed");
    const shipped = screen.getByText("Shipped");

    // Pending and Confirmed should have darker text (completed)
    expect(pending.className).toContain("text-charcoal");
    expect(confirmed.className).toContain("text-charcoal");
    // Shipped should be gray (future)
    expect(shipped.className).toContain("text-gray-400");
  });

  it("shows 3 filled steps for shipped", () => {
    renderWithIntl(<StatusTimeline currentStatus="shipped" />);
    const shipped = screen.getByText("Shipped");
    const delivered = screen.getByText("Delivered");

    expect(shipped.className).toContain("text-charcoal");
    expect(delivered.className).toContain("text-gray-400");
  });

  it("shows all 4 steps filled for delivered", () => {
    renderWithIntl(<StatusTimeline currentStatus="delivered" />);
    const delivered = screen.getByText("Delivered");
    expect(delivered.className).toContain("text-charcoal");
  });

  it("shows 'Pending → Cancelled' for cancelled status", () => {
    renderWithIntl(<StatusTimeline currentStatus="cancelled" />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
    // Should NOT show the normal progression steps
    expect(screen.queryByText("Confirmed")).not.toBeInTheDocument();
    expect(screen.queryByText("Shipped")).not.toBeInTheDocument();
    expect(screen.queryByText("Delivered")).not.toBeInTheDocument();
  });
});
