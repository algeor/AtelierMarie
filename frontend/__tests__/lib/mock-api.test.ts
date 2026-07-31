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

describe("mock-api delivery place search", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("matches door-delivery places by postcode", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    const places = await getDeliveryPlaces("econt", "5972");

    expect(places).toEqual([{ name: "Искър", region: "Плевен", postal_code: "5972" }]);
  });

  it("does not collapse same-name and same-region places with different postcodes", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    const places = await getDeliveryPlaces("speedy", "Искър");

    expect(places).toEqual([
      { name: "Искър", region: "Плевен", postal_code: "5868" },
      { name: "Искър", region: "Плевен", postal_code: "5972" },
    ]);
  });

  it("matches a settlement by the second word in its name", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    const places = await getDeliveryPlaces("econt", "Пазар");

    expect(places).toContainEqual({ name: "Нови Пазар", region: "Шумен", postal_code: "9900" });
  });

  it("requires every token in a combined region and postcode query", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    const places = await getDeliveryPlaces("econt", "Плевен 5972");

    expect(places).toEqual([{ name: "Искър", region: "Плевен", postal_code: "5972" }]);
  });

  it("includes manually supplemented door-delivery villages for both couriers", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    const expected = { name: "Згориград", region: "Враца", postal_code: "3042" };

    expect(await getDeliveryPlaces("econt", "Згор")).toEqual([expected]);
    expect(await getDeliveryPlaces("speedy", "Згор")).toEqual([expected]);
  });

  it("includes Roman for Speedy from the served-place supplement", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    expect(await getDeliveryPlaces("speedy", "Роман")).toEqual([
      { name: "Роман", region: "Враца", postal_code: "3130" },
    ]);
  });

  it("can expose Speedy office-city backfills without a known postcode", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    expect(await getDeliveryPlaces("speedy", "Батак")).toEqual([
      { name: "Батак", region: null, postal_code: null },
    ]);
  });

  it("keeps the exact city ahead of broader region matches", async () => {
    const { getDeliveryPlaces } = await import("@/lib/mock-api");

    const places = await getDeliveryPlaces("econt", "Пловдив");

    expect(places[0]).toEqual({ name: "Пловдив", region: "Пловдив", postal_code: "4000" });
    expect(places).toContainEqual({ name: "Садово", region: "Пловдив", postal_code: "4122" });
  });
});
