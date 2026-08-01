"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  TRACKING_CARRIERS,
  buildTrackingUrl,
  carrierLabel,
  type TrackingCarrier,
} from "@/lib/tracking";
import type { Courier } from "@/lib/types";

export interface ShipTrackingInput {
  tracking_number: string;
  tracking_carrier: string;
  tracking_url?: string;
}

interface ShipOrderModalProps {
  orderId: string;
  deliveryCourier?: Courier | null;
  isSubmitting: boolean;
  onCancel: () => void;
  onConfirm: (tracking: ShipTrackingInput) => void;
}

/**
 * Shipping form shown when an admin marks an order "shipped".
 * Collects tracking number + carrier, previews the auto-generated URL (or
 * accepts a manual URL for "other"), and blocks submit until a number is
 * entered — mirroring the backend's TRACKING_REQUIRED rule (task 10.1–10.4).
 */
export function ShipOrderModal({
  orderId,
  deliveryCourier = null,
  isSubmitting,
  onCancel,
  onConfirm,
}: ShipOrderModalProps) {
  const t = useTranslations("admin.ship");
  const [carrier, setCarrier] = useState<TrackingCarrier>(deliveryCourier ?? "speedy");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [customUrl, setCustomUrl] = useState("");
  const [touched, setTouched] = useState(false);
  const [mismatchAcknowledged, setMismatchAcknowledged] = useState(false);

  const trimmedNumber = trackingNumber.trim();
  const numberMissing = trimmedNumber.length === 0;
  const autoUrl = buildTrackingUrl(carrier, trimmedNumber);
  const isOther = autoUrl === null;
  const previewUrl = isOther ? customUrl.trim() || null : autoUrl;
  const carrierMismatch = Boolean(deliveryCourier && carrier !== deliveryCourier);
  const deliveryCourierLabel = carrierLabel(deliveryCourier);
  const selectedCarrierLabel = carrierLabel(carrier);

  function handleSubmit() {
    setTouched(true);
    if (numberMissing) return;
    if (carrierMismatch && !mismatchAcknowledged) {
      setMismatchAcknowledged(true);
      return;
    }
    const tracking: ShipTrackingInput = {
      tracking_number: trimmedNumber,
      tracking_carrier: carrier,
    };
    // Only send a URL for "other" (manual); known carriers auto-generate server-side.
    if (isOther && customUrl.trim()) {
      tracking.tracking_url = customUrl.trim();
    }
    onConfirm(tracking);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("title")}
    >
      <div className="w-full max-w-md rounded-brand border border-champagne-beige bg-cream p-6 shadow-lg">
        <h2 className="font-heading text-lg font-semibold text-charcoal">
          {t("title")} #{orderId.slice(0, 8)}
        </h2>
        {deliveryCourierLabel && (
          <p className="mt-2 text-sm text-soft-brown">
            {t("deliveryCourier", { courier: deliveryCourierLabel })}
          </p>
        )}

        <div className="mt-4 space-y-4">
          <div>
            <label
              htmlFor="ship-carrier"
              className="block text-sm font-medium text-charcoal"
            >
              {t("carrier")}
            </label>
            <select
              id="ship-carrier"
              value={carrier}
              onChange={(e) => {
                setCarrier(e.target.value as TrackingCarrier);
                setMismatchAcknowledged(false);
              }}
              className="mt-1 h-9 w-full rounded-brand border border-champagne-beige bg-cream px-2 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
            >
              {TRACKING_CARRIERS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            {carrierMismatch && (
              <p className="mt-2 rounded-brand border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800" role="alert">
                {t("carrierMismatch", {
                  delivery: deliveryCourierLabel ?? deliveryCourier ?? "delivery",
                  selected: selectedCarrierLabel ?? carrier,
                })}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="ship-tracking-number"
              className="block text-sm font-medium text-charcoal"
            >
              {t("trackingNumber")}
            </label>
            <input
              id="ship-tracking-number"
              type="text"
              value={trackingNumber}
              onChange={(e) => setTrackingNumber(e.target.value)}
              onBlur={() => setTouched(true)}
              aria-invalid={touched && numberMissing}
              className="mt-1 h-9 w-full rounded-brand border border-champagne-beige bg-cream px-2 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
            />
            {touched && numberMissing && (
              <p className="mt-1 text-xs text-red-600">{t("trackingRequired")}</p>
            )}
          </div>

          {isOther ? (
            <div>
              <label
                htmlFor="ship-tracking-url"
                className="block text-sm font-medium text-charcoal"
              >
                {t("trackingUrl")}
              </label>
              <input
                id="ship-tracking-url"
                type="url"
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                placeholder={t("customUrlPlaceholder")}
                className="mt-1 h-9 w-full rounded-brand border border-champagne-beige bg-cream px-2 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
              />
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium text-charcoal">{t("urlPreview")}</p>
              <p className="mt-1 truncate text-xs text-soft-brown" title={previewUrl ?? ""}>
                {previewUrl ?? t("urlAuto")}
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-brand px-4 py-2 text-sm text-soft-brown hover:bg-champagne-beige disabled:opacity-50"
          >
            {t("cancel")}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || numberMissing}
            className="rounded-brand bg-muted-gold px-4 py-2 text-sm font-medium text-charcoal hover:bg-muted-gold/80 disabled:opacity-50"
          >
            {carrierMismatch && mismatchAcknowledged ? t("confirmMismatch") : t("confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
