/**
 * Shared utility functions.
 */

/**
 * Format a price in cents to a display string.
 * Example: formatPrice(3200) => "$32.00"
 */
export function formatPrice(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}
