import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusTimeline } from "@/components/orders/StatusTimeline";

describe("StatusTimeline", () => {
  it("shows 1 filled step for pending status", () => {
    render(<StatusTimeline currentStatus="pending" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(4);
    expect(items[0]).toHaveTextContent("Pending");
    expect(items[1]).toHaveTextContent("Confirmed");
    expect(items[2]).toHaveTextContent("Shipped");
    expect(items[3]).toHaveTextContent("Delivered");
  });

  it("shows 2 filled steps for confirmed status", () => {
    render(<StatusTimeline currentStatus="confirmed" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(4);
    // Pending and Confirmed should be filled (have font-medium text-charcoal)
    expect(items[0]?.querySelector("span")).toHaveClass("font-medium");
    expect(items[1]?.querySelector("span")).toHaveClass("font-medium");
    // Shipped and Delivered should be gray
    expect(items[2]?.querySelector("span")).toHaveClass("text-gray-400");
    expect(items[3]?.querySelector("span")).toHaveClass("text-gray-400");
  });

  it("shows 3 filled steps for shipped status", () => {
    render(<StatusTimeline currentStatus="shipped" />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]?.querySelector("span")).toHaveClass("font-medium");
    expect(items[1]?.querySelector("span")).toHaveClass("font-medium");
    expect(items[2]?.querySelector("span")).toHaveClass("font-medium");
    expect(items[3]?.querySelector("span")).toHaveClass("text-gray-400");
  });

  it("shows 4 filled steps for delivered status", () => {
    render(<StatusTimeline currentStatus="delivered" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(4);
    items.forEach((item) => {
      expect(item.querySelector("span")).toHaveClass("font-medium");
    });
  });

  it("shows Pending → Cancelled for cancelled status", () => {
    render(<StatusTimeline currentStatus="cancelled" />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Pending");
    expect(items[1]).toHaveTextContent("Cancelled");
  });
});
