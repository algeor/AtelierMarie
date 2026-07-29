const DEFAULT_API_URL = "http://localhost:8000";

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

const API_URL = stripTrailingSlash(process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL);
const configuredMediaUrl = process.env.NEXT_PUBLIC_MEDIA_URL?.trim();

export const MEDIA_URL = (() => {
  if (configuredMediaUrl) return stripTrailingSlash(configuredMediaUrl);
  if (process.env.NEXT_PUBLIC_USE_MOCK_API === "true") return "";
  return API_URL;
})();

export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (!url.startsWith("/static/")) return url;
  return MEDIA_URL ? `${MEDIA_URL}${url}` : url;
}
