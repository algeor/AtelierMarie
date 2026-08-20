import type { MetadataRoute } from "next";
import { BASE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/admin/",
        "/en/admin/",
        "/bg/admin/",
        "/account/",
        "/en/account/",
        "/bg/account/",
        "/checkout/",
        "/en/checkout/",
        "/bg/checkout/",
        "/orders/",
        "/en/orders/",
        "/bg/orders/",
        "/auth/",
        "/en/auth/",
        "/bg/auth/",
        "/design-system/",
      ],
    },
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
