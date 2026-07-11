import createMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";

const handleI18nRouting = createMiddleware(routing);

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

  return handleI18nRouting(request);
}

export const config = {
  // Match all pathnames except:
  // - API routes (_next, api)
  // - Static files (images, favicon, etc.)
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
