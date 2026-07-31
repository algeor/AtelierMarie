import { beforeEach, describe, expect, it, vi } from "vitest";

const SPEEDY_ORDER_ID = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d";
const ECONT_ORDER_ID = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e";

describe("mock-api order shipping", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("auto-creates Speedy tracking when shipping a Speedy order", async () => {
    const { updateOrderStatus } = await import("@/lib/mock-api");

    await updateOrderStatus(SPEEDY_ORDER_ID, "confirmed");
    const shipped = await updateOrderStatus(SPEEDY_ORDER_ID, "shipped");

    expect(shipped.status).toBe("shipped");
    expect(shipped.tracking_number).toBe("63689182611");
    expect(shipped.tracking_carrier).toBe("speedy");
    expect(shipped.tracking_url).toBe(
      "https://www.speedy.bg/en/track-shipment?shipmentNumber=63689182611",
    );
  });

  it("still requires manual tracking when shipping a non-Speedy order", async () => {
    const { updateOrderStatus } = await import("@/lib/mock-api");

    await expect(updateOrderStatus(ECONT_ORDER_ID, "shipped")).rejects.toMatchObject({
      code: "TRACKING_REQUIRED",
    });
  });
});
