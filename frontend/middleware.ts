import createMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";
import {
  buildContentSecurityPolicy,
  createCspNonce,
  CSP_HEADER,
  CSP_NONCE_HEADER,
  HSTS_HEADER,
  HSTS_HEADER_VALUE,
} from "./lib/security-headers";

const handleI18nRouting = createMiddleware(routing);
const LOCALE_COOKIE = "NEXT_LOCALE";

function detectLocale(request: NextRequest): "en" | "bg" {
  const cookieLocale = request.cookies.get(LOCALE_COOKIE)?.value;
  if (cookieLocale === "en" || cookieLocale === "bg") return cookieLocale;

  const acceptLanguage = request.headers.get("accept-language") ?? "";
  return /\bbg\b/i.test(acceptLanguage) ? "bg" : "en";
}

function hasLocalePrefix(pathname: string): boolean {
  return /^\/(en|bg)(\/|$)/i.test(pathname);
}

function applySecurityHeaders(response: NextResponse, nonce: string): NextResponse {
  const contentSecurityPolicy = buildContentSecurityPolicy(nonce);
  response.headers.set(CSP_HEADER, contentSecurityPolicy);
  response.headers.set(HSTS_HEADER, HSTS_HEADER_VALUE);
  response.headers.set("Cross-Origin-Opener-Policy", "same-origin-allow-popups");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-DNS-Prefetch-Control", "off");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set(
    "Permissions-Policy",
    'camera=(), microphone=(), geolocation=(self "https://delivery.econt.com" "https://delivery-demo.econt.com")'
  );
  return response;
}

export default function middleware(request: NextRequest) {
  const nonce = createCspNonce();
  const requestHeaders = new Headers(request.headers);
  const contentSecurityPolicy = buildContentSecurityPolicy(nonce);
  requestHeaders.set(CSP_HEADER, contentSecurityPolicy);
  requestHeaders.set(CSP_NONCE_HEADER, nonce);

  const { pathname } = request.nextUrl;
  const [, firstSegment, ...rest] = pathname.split("/");

  if (
    firstSegment &&
    /^[a-z]{2}$/i.test(firstSegment) &&
    !routing.locales.includes(firstSegment as "en" | "bg")
  ) {
    const url = request.nextUrl.clone();
    url.pathname = `/en${rest.length > 0 ? `/${rest.join("/")}` : ""}`;
    return applySecurityHeaders(NextResponse.redirect(url), nonce);
  }

  if (!hasLocalePrefix(pathname)) {
    const locale = detectLocale(request);
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}${pathname === "/" ? "/" : pathname}`;
    const response = NextResponse.redirect(url, 307);
    response.cookies.set(LOCALE_COOKIE, locale, {
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
      sameSite: "lax",
    });
    return applySecurityHeaders(response, nonce);
  }

  const response = handleI18nRouting(
    new NextRequest(request.url, {
      headers: requestHeaders,
      method: request.method,
      body: request.body,
      redirect: request.redirect,
      signal: request.signal,
    })
  );
  return applySecurityHeaders(response, nonce);
}

export const config = {
  // Match all pathnames except:
  // - API routes (_next, api)
  // - The design-system gallery (lives outside [locale], must not be locale-prefixed)
  // - Static files (images, favicon, etc.)
  matcher: ["/((?!api|_next|design-system|.*\\..*).*)"],
};
