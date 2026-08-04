"use client";

/**
 * DeliveryDetails — read-only display of a stored delivery choice.
 * Used by order confirmation, customer order detail, and admin order views.
 *
 * Per Decision 6 / task 4.6, legacy `shipping_address` has been ripped out
 * server-side — this component only handles the structured `delivery_*` fields.
 */

import { useTranslations } from "next-intl";
import type { DeliveryDoor, DeliveryOffice, OrderResponse } from "@/lib/types";

interface DeliveryDetailsProps {
  order: Pick<OrderResponse, "delivery_method" | "delivery_courier" | "delivery_details">;
}

export function DeliveryDetails({ order }: DeliveryDetailsProps) {
  const t = useTranslations("checkout.delivery.display");
  const tMethod = useTranslations("checkout.delivery.method");
  const tCourier = useTranslations("checkout.delivery.courier");
  const tOfficeType = useTranslations("checkout.delivery.officeType");

  if (!order.delivery_method) return null;

  const isOffice = order.delivery_method === "office";
  const officeDetails = isOffice ? (order.delivery_details as DeliveryOffice | null) : null;
  const doorDetails = !isOffice ? (order.delivery_details as DeliveryDoor | null) : null;

  return (
    <section className="mt-8 border-t border-border/60 pt-6">
      <h2 className="mb-3 text-sm font-medium text-text">{t("sectionTitle")}</h2>

      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
        <dt className="text-muted">{t("methodLabel")}</dt>
        <dd className="text-text">{tMethod(order.delivery_method)}</dd>

        {order.delivery_courier && (
          <>
            <dt className="text-muted">{t("courierLabel")}</dt>
            <dd className="text-text">{tCourier(order.delivery_courier)}</dd>
          </>
        )}

        {officeDetails && (
          <>
            <dt className="text-muted">{t("officeLabel")}</dt>
            <dd className="text-text">
              {officeDetails.office_type === "apt" ? "🔐 " : "📦 "}
              {officeDetails.office_name}
              <span className="ml-2 text-xs text-muted">
                ({tOfficeType(officeDetails.office_type)})
              </span>
            </dd>
            <dt className="text-muted">{t("phoneLabel")}</dt>
            <dd className="text-text">{officeDetails.phone}</dd>
          </>
        )}

        {doorDetails && (
          <>
            <dt className="text-muted">{t("addressLabel")}</dt>
            <dd className="text-text">
              {doorDetails.street}
              {doorDetails.building && `, ${t("building")} ${doorDetails.building}`}
              {doorDetails.apartment && `, ${t("apartment")} ${doorDetails.apartment}`}
              <br />
              <span className="text-muted">
                {doorDetails.postal_code} {doorDetails.city}
              </span>
            </dd>
            <dt className="text-muted">{t("phoneLabel")}</dt>
            <dd className="text-text">{doorDetails.phone}</dd>
          </>
        )}
      </dl>
    </section>
  );
}
