/**
 * Shipment tracking helpers — carrier definitions and tracking URL patterns.
 * Mirrors the backend's supported carriers (app/services/order_service.py).
 */

export const TRACKING_CARRIERS = [
  { value: "speedy", label: "Speedy" },
  { value: "econt", label: "Econt" },
  { value: "dhl", label: "DHL" },
  { value: "fedex", label: "FedEx" },
  { value: "other", label: "Other" },
] as const;

export type TrackingCarrier = (typeof TRACKING_CARRIERS)[number]["value"];

/**
 * Build the public tracking URL for a carrier + tracking number.
 * Returns null when the carrier has no known URL pattern ("other") or the
 * tracking number is blank — matching the backend's auto-generation rules.
 */
export function buildTrackingUrl(
  carrier: string,
  trackingNumber: string
): string | null {
  const num = encodeURIComponent(trackingNumber.trim());
  if (!num) return null;
  switch (carrier) {
    case "speedy":
      return `https://www.speedy.bg/en/track-shipment?shipmentNumber=${num}`;
    case "econt":
      return `https://www.econt.com/services/track-shipment/${num}`;
    case "dhl":
      return `https://www.dhl.com/en/express/tracking.html?AWB=${num}`;
    case "fedex":
      return `https://www.fedex.com/fedextrack/?trknbr=${num}`;
    default:
      return null;
  }
}

/** Human-readable label for a carrier value (falls back to the raw value). */
export function carrierLabel(carrier: string | null): string | null {
  if (!carrier) return null;
  const found = TRACKING_CARRIERS.find((c) => c.value === carrier);
  return found ? found.label : carrier;
}
