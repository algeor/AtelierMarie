/**
 * Shared client constants that mirror the backend `app/constants.py` source of
 * truth. Keep these in sync with the backend; drift means the UI can show
 * "free shipping" while the server charges (or vice-versa).
 *
 * If these ever need to be authoritative at runtime, expose them via a bootstrap
 * config endpoint rather than duplicating the literal — see review W5.
 */

// Orders with an items subtotal at or above this get free shipping.
// Mirrors app/constants.py FREE_SHIPPING_THRESHOLD_CENTS.
export const FREE_SHIPPING_THRESHOLD_CENTS = 5000; // €50

// Flat last-resort shipping price when a courier calculate API is unavailable.
// Mirrors app/constants.py FALLBACK_SHIPPING_CENTS.
export const FALLBACK_SHIPPING_CENTS = 500; // €5

// Fixed in-house delivery price when no courier delivery methods are available.
// Mirrors app/constants.py INTERNAL_DELIVERY_CENTS.
export const INTERNAL_DELIVERY_CENTS = 350; // €3.50
