const DIRECTIVE_SEPARATOR = "; ";
const NONCE_BYTES = 16;

function originFromUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function unique(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))));
}

export const CSP_NONCE_HEADER = "x-nonce";
export const CSP_HEADER = "Content-Security-Policy";
export const HSTS_HEADER = "Strict-Transport-Security";
export const HSTS_HEADER_VALUE = "max-age=31536000; includeSubDomains; preload";

export function createCspNonce(): string {
  const bytes = new Uint8Array(NONCE_BYTES);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes));
}

export function buildContentSecurityPolicy(nonce: string): string {
  const apiOrigin = originFromUrl(process.env.NEXT_PUBLIC_API_URL);
  const mediaOrigin = originFromUrl(process.env.NEXT_PUBLIC_MEDIA_URL);
  const siteOrigin = originFromUrl(process.env.NEXT_PUBLIC_SITE_URL);
  const isDevelopment = process.env.NODE_ENV === "development";

  const connectSources = unique([
    "'self'",
    apiOrigin,
    siteOrigin,
    isDevelopment ? "http://localhost:8000" : null,
    isDevelopment ? "http://127.0.0.1:8000" : null,
    isDevelopment ? "ws://localhost:*" : null,
    isDevelopment ? "ws://127.0.0.1:*" : null,
  ]);

  const imageSources = unique(["'self'", "data:", "blob:", mediaOrigin, apiOrigin, "https:"]);
  const mediaSources = unique(["'self'", "blob:", mediaOrigin, apiOrigin, "https:"]);

  const directives = [
    ["default-src", "'self'"],
    ["base-uri", "'self'"],
    ["object-src", "'none'"],
    ["frame-ancestors", "'none'"],
    ["form-action", "'self'"],
    [
      "script-src",
      "'self'",
      `'nonce-${nonce}'`,
      "'strict-dynamic'",
      "https:",
      ...(isDevelopment ? ["http:"] : []),
      ...(isDevelopment ? ["'unsafe-eval'"] : []),
    ],
    ["style-src", "'self'"],
    ["style-src-elem", "'self'", `'nonce-${nonce}'`],
    ["style-src-attr", "'unsafe-inline'"],
    ["img-src", ...imageSources],
    ["font-src", "'self'", "data:"],
    ["connect-src", ...connectSources],
    ["frame-src", "'self'", "https://delivery.econt.com", "https://delivery-demo.econt.com"],
    ["child-src", "'self'", "blob:", "https://delivery.econt.com", "https://delivery-demo.econt.com"],
    ["media-src", ...mediaSources],
    ["worker-src", "'self'", "blob:"],
    ["manifest-src", "'self'"],
    ...(isDevelopment ? [] : [["upgrade-insecure-requests"]]),
  ];

  return directives.map((directive) => directive.join(" ")).join(DIRECTIVE_SEPARATOR);
}
