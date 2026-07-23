import React from "react";
import { screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { ShipOrderModal } from "@/components/admin/ShipOrderModal";

function setup(overrides: Partial<React.ComponentProps<typeof ShipOrderModal>> = {}) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  renderWithIntl(
    <ShipOrderModal
      orderId="a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
      isSubmitting={false}
      onCancel={onCancel}
      onConfirm={onConfirm}
      {...overrides}
    />
  );
  return { onConfirm, onCancel };
}

describe("ShipOrderModal", () => {
  it("blocks submit until a tracking number is entered", () => {
    const { onConfirm } = setup();
    const confirm = screen.getByRole("button", { name: "Mark as shipped" });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("shows an auto-generated URL preview for a known carrier", () => {
    setup();
    fireEvent.change(screen.getByLabelText("Tracking number"), {
      target: { value: "123456" },
    });
    // Default carrier is speedy → speedy pattern preview.
    expect(
      screen.getByText(
        "https://www.speedy.bg/en/track-shipment?shipmentNumber=123456"
      )
    ).toBeInTheDocument();
  });

  it("confirms with tracking data for a known carrier (no explicit URL)", () => {
    const { onConfirm } = setup();
    fireEvent.change(screen.getByLabelText("Carrier"), {
      target: { value: "econt" },
    });
    fireEvent.change(screen.getByLabelText("Tracking number"), {
      target: { value: "  77  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Mark as shipped" }));
    expect(onConfirm).toHaveBeenCalledWith({
      tracking_number: "77",
      tracking_carrier: "econt",
    });
  });

  it("accepts a manual URL for the 'other' carrier", () => {
    const { onConfirm } = setup();
    fireEvent.change(screen.getByLabelText("Carrier"), {
      target: { value: "other" },
    });
    fireEvent.change(screen.getByLabelText("Tracking number"), {
      target: { value: "XYZ" },
    });
    fireEvent.change(screen.getByLabelText("Tracking URL"), {
      target: { value: "https://custom.example/track/XYZ" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Mark as shipped" }));
    expect(onConfirm).toHaveBeenCalledWith({
      tracking_number: "XYZ",
      tracking_carrier: "other",
      tracking_url: "https://custom.example/track/XYZ",
    });
  });

  it("cancels without confirming", () => {
    const { onCancel, onConfirm } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
