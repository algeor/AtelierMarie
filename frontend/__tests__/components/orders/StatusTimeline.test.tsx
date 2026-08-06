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

    // Pending and Confirmed should use primary text (completed)
    expect(pending.className).toContain("text-text");
    expect(confirmed.className).toContain("text-text");
    // Shipped should be muted (future)
    expect(shipped.className).toContain("text-muted/55");
  });

  it("shows 3 filled steps for shipped", () => {
    renderWithIntl(<StatusTimeline currentStatus="shipped" />);
    const shipped = screen.getByText("Shipped");
    const delivered = screen.getByText("Delivered");

    expect(shipped.className).toContain("text-text");
    expect(delivered.className).toContain("text-muted/55");
  });

  it("shows all 4 steps filled for delivered", () => {
    renderWithIntl(<StatusTimeline currentStatus="delivered" />);
    const delivered = screen.getByText("Delivered");
    expect(delivered.className).toContain("text-text");
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

  it("renders the Speedy tracking number and track link once shipped", () => {
    renderWithIntl(
      <StatusTimeline
        currentStatus="shipped"
        trackingNumber="63689182611"
        trackingCarrier="speedy"
        trackingUrl="https://www.speedy.bg/en/track-shipment?shipmentNumber=63689182611"
      />,
    );
    // The Speedy-generated tracking number is surfaced on the shipped step.
    expect(screen.getByText("63689182611")).toBeInTheDocument();
    // And a track-package link points at the carrier URL.
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute(
      "href",
      "https://www.speedy.bg/en/track-shipment?shipmentNumber=63689182611",
    );
  });

  it("does not render tracking block before the order has shipped", () => {
    renderWithIntl(
      <StatusTimeline currentStatus="confirmed" trackingNumber="63689182611" />,
    );
    // Tracking is only shown on/after the reached shipped step.
    expect(screen.queryByText("63689182611")).not.toBeInTheDocument();
  });
});
