import { describe, expect, it } from "vitest";

import {
  addToCart,
  createEcontLabel,
  createOrder,
  getAdminOrder,
  getEcontOrderReadiness,
  getOrder,
  refreshEcontTrace,
  updateOrderStatus,
  updateEcontSettings,
} from "@/lib/mock-api";

describe("Econt fake-client flow", () => {
  it("runs checkout -> admin label -> customer tracking with mock Econt", async () => {
    await updateEcontSettings({
      enabled: true,
      environment: "demo",
      shop_id: "mock-shop-1",
      sender_delivery_mode: "office",
      sender_office_code: "1127",
      default_pack_count: 1,
      shipment_description: "Atelier Marie order",
    });

    await addToCart("lavender-dreams-300ml", 1);
    const order = await createOrder({
      customer_email: "econt-flow@example.com",
      customer_name: "Econt Flow",
      payment_method: "cod",
      notes: null,
      delivery: {
        method: "office",
        door: null,
        office: {
          courier: "econt",
          office_id: "econt-sf-001",
          office_code: "1127",
          office_name: "Econt Sofia Center",
          office_type: "office",
          city: "Sofia",
          phone: "+359888123456",
        },
      },
    });

    expect(order.delivery_courier).toBe("econt");
    expect(order.delivery_details).toMatchObject({ office_code: "1127" });

    await updateOrderStatus(order.id, "confirmed");

    const readiness = await getEcontOrderReadiness(order.id);
    expect(readiness.ready).toBe(true);
    expect(readiness.blockers).toEqual([]);

    const label = await createEcontLabel(order.id);
    expect(label.shipment_number).toMatch(/^EC\d+$/);
    expect(label.label_url).toBe(
      `https://delivery-demo.econt.com/labels/${label.shipment_number}.pdf`,
    );

    const adminOrder = await getAdminOrder(order.id);
    expect(adminOrder.courier_provider).toBe("econt");
    expect(adminOrder.courier_shipment_number).toBe(label.shipment_number);
    expect(adminOrder.tracking_url).toBe(
      `https://www.econt.com/services/track-shipment/${label.shipment_number}`,
    );

    await refreshEcontTrace(order.id);
    const customerOrder = await getOrder(order.id);
    expect(customerOrder.courier_sync_status).toBe("trace_synced");
    expect(customerOrder.courier_shipment_number).toBe(label.shipment_number);
    expect(customerOrder.tracking_carrier).toBe("econt");
    expect(customerOrder.tracking_url).toBe(
      `https://www.econt.com/services/track-shipment/${label.shipment_number}`,
    );
  });
});
