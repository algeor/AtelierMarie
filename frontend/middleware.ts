import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Match all pathnames except:
  // - API routes (_next, api)
  // - Static files (images, favicon, etc.)
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
