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

/**
 * Stored datetime → `datetime-local` value in local time.
 *
 * Accepts the real API's canonical `YYYY-MM-DD HH:MM:SS` (UTC by convention) and
 * also already-ISO strings with `T`/`Z`/offset (as the mock stores), so editing
 * never silently drops a date regardless of which backend produced it.
 */
export function storedUtcToLocalInput(utc: string | null): string {
  if (!utc) return "";
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(utc);
  const iso = utc.includes("T") ? utc : utc.replace(" ", "T");
  const d = new Date(hasTz ? iso : iso + "Z");
  return isNaN(d.getTime()) ? "" : toDatetimeLocal(d);
}

/** `datetime-local` value (local time) → timezone-aware UTC ISO string, or null. */
export function localInputToUtcIso(local: string): string | null {
  if (!local) return null;
  const d = new Date(local);
  return isNaN(d.getTime()) ? null : d.toISOString();
}
