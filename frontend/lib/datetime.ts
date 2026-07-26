/**
 * Shared datetime helpers for admin discount/banner windows.
 *
 * Backend stores canonical UTC text (`YYYY-MM-DD HH:MM:SS`). Browsers edit in
 * local time via `datetime-local` inputs. These helpers convert between the two
 * so the promotions UI matches the single-product discount form exactly.
 */

/** Format a Date into a `datetime-local` input value (browser-local time). */
export function toDatetimeLocal(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/** Stored UTC text (`YYYY-MM-DD HH:MM:SS`) → `datetime-local` value in local time. */
export function storedUtcToLocalInput(utc: string | null): string {
  if (!utc) return "";
  const d = new Date(utc.replace(" ", "T") + "Z");
  return isNaN(d.getTime()) ? "" : toDatetimeLocal(d);
}

/** `datetime-local` value (local time) → timezone-aware UTC ISO string, or null. */
export function localInputToUtcIso(local: string): string | null {
  if (!local) return null;
  const d = new Date(local);
  return isNaN(d.getTime()) ? null : d.toISOString();
}
