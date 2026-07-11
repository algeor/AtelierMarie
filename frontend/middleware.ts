import createMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";

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

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const [, firstSegment, ...rest] = pathname.split("/");

  if (
    firstSegment &&
    /^[a-z]{2}$/i.test(firstSegment) &&
    !routing.locales.includes(firstSegment as "en" | "bg")
  ) {
    const url = request.nextUrl.clone();
    url.pathname = `/en${rest.length > 0 ? `/${rest.join("/")}` : ""}`;
    return NextResponse.redirect(url);
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
    return response;
  }

  return handleI18nRouting(request);
}

export const config = {
  // Match all pathnames except:
  // - API routes (_next, api)
  // - Static files (images, favicon, etc.)
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
