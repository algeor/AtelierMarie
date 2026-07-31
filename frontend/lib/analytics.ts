import { BASE_URL } from "./api-client";

export const CONSENT_COOKIE_NAME = "atelier_cookie_consent";
export const CONSENT_VERSION = process.env.NEXT_PUBLIC_ANALYTICS_CONSENT_VERSION || "2026-07-31";
const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

export type AnalyticsEventType =
  | "product_view"
  | "listing_filter"
  | "add_to_cart"
  | "cart_open"
  | "checkout_start"
  | "delivery_selected"
  | "shipping_quote_selected"
  | "order_submit"
  | "payment_redirect"
  | "purchase_confirmed";

export interface ConsentPreference {
  version: string;
  analytics: boolean;
  locale: "en" | "bg";
  updatedAt: string;
}

export interface AnalyticsEventPayload {
  event_id: string;
  event_type: AnalyticsEventType;
  occurred_at: string;
  locale: "en" | "bg";
  page_path?: string;
  properties: Record<string, string | number | boolean | null | undefined>;
}

let analyticsAllowed = false;
let queue: AnalyticsEventPayload[] = [];
let flushInFlight = false;

function getLocaleFromPath(): "en" | "bg" {
  if (typeof window === "undefined") return "en";
  return window.location.pathname.startsWith("/bg") ? "bg" : "en";
}

function eventId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function readConsentPreference(): ConsentPreference | null {
  if (typeof document === "undefined") return null;
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${CONSENT_COOKIE_NAME}=`));
  if (!cookie) return null;
  try {
    return JSON.parse(decodeURIComponent(cookie.split("=")[1] || "")) as ConsentPreference;
  } catch {
    return null;
  }
}

export function writeConsentPreference(analytics: boolean, locale = getLocaleFromPath()) {
  if (typeof document === "undefined") return;
  const preference: ConsentPreference = {
    version: CONSENT_VERSION,
    analytics,
    locale,
    updatedAt: new Date().toISOString(),
  };
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${CONSENT_COOKIE_NAME}=${encodeURIComponent(
    JSON.stringify(preference)
  )}; Max-Age=31536000; Path=/; SameSite=Lax${secure}`;
}

export async function syncConsentPreference(analytics: boolean, locale = getLocaleFromPath()) {
  if (typeof window === "undefined" || USE_MOCK_API) return;
  const response = await fetch(`${BASE_URL}/v1/analytics/consent`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ analytics, consent_version: CONSENT_VERSION, locale }),
  });
  if (!response.ok) {
    throw new Error("Analytics consent could not be recorded");
  }
}

export function hasCurrentAnalyticsConsent(): boolean {
  const preference = readConsentPreference();
  return preference?.version === CONSENT_VERSION && preference.analytics === true;
}

export function setAnalyticsConsent(allowed: boolean) {
  analyticsAllowed = allowed;
  if (!allowed) {
    queue = [];
    return;
  }
  void flushAnalyticsQueue();
}

export function clearAnalyticsQueue() {
  queue = [];
}

export function trackAnalytics(
  eventType: AnalyticsEventType,
  properties: AnalyticsEventPayload["properties"] = {},
  locale = getLocaleFromPath()
) {
  if (!analyticsAllowed || typeof window === "undefined") return;
  const payload: AnalyticsEventPayload = {
    event_id: eventId(),
    event_type: eventType,
    occurred_at: new Date().toISOString(),
    locale,
    page_path: window.location.pathname,
    properties,
  };
  queue.push(payload);
  void flushAnalyticsQueue();
}

export async function flushAnalyticsQueue() {
  if (!analyticsAllowed || flushInFlight || queue.length === 0 || typeof window === "undefined") {
    return;
  }
  flushInFlight = true;
  const batch = queue.slice(0, 25);
  const body = JSON.stringify({ events: batch });
  const url = `${BASE_URL}/v1/analytics/events`;

  try {
    if (USE_MOCK_API) {
      const target = globalThis as typeof globalThis & { __atelierAnalyticsEvents?: AnalyticsEventPayload[] };
      target.__atelierAnalyticsEvents = [...(target.__atelierAnalyticsEvents || []), ...batch];
      queue = queue.slice(batch.length);
      return;
    }
    const blob = new Blob([body], { type: "application/json" });
    const beaconSent = navigator.sendBeacon?.(url, blob) === true;
    if (!beaconSent) {
      await fetch(url, {
        method: "POST",
        credentials: "include",
        keepalive: true,
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body,
      });
    }
    queue = queue.slice(batch.length);
  } catch {
    queue = [...batch, ...queue.slice(batch.length)].slice(0, 50);
  } finally {
    flushInFlight = false;
  }
}

export function getMockAnalyticsEvents(): AnalyticsEventPayload[] {
  const target = globalThis as typeof globalThis & { __atelierAnalyticsEvents?: AnalyticsEventPayload[] };
  return target.__atelierAnalyticsEvents || [];
}

if (typeof window !== "undefined") {
  setAnalyticsConsent(hasCurrentAnalyticsConsent());
  window.addEventListener("pagehide", () => {
    void flushAnalyticsQueue();
  });
}
