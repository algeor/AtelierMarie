import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with conflict resolution.
 * Uses clsx for conditional logic and tailwind-merge for deduplication.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a price in cents to a display string.
 * Uses euro prefix with period decimal separator (luxury brand aesthetic).
 * Example: formatPrice(3200) => "€32.00"
 * Throws on negative, NaN, or Infinity.
 */
export function formatPrice(cents: number): string {
  if (!Number.isFinite(cents) || cents < 0) {
    throw new Error(`Invalid price value: ${cents}`);
  }
  const euros = cents / 100;
  return `€${euros.toFixed(2)}`;
}
