import { describe, expect, it } from "vitest";
import en from "@/messages/en.json";
import bg from "@/messages/bg.json";

describe("analytics policy and localized copy", () => {
  it("cookie and privacy policies no longer claim there is no analytics", () => {
    const combined = JSON.stringify({ en: { privacy: en.privacy, cookies: en.cookies }, bg: { privacy: bg.privacy, cookies: bg.cookies } });

    expect(combined).toContain("first-party analytics");
    expect(combined).toContain("първостранна аналитика");
    expect(combined).toContain("atelier_cookie_consent");
    expect(combined).not.toContain("contains no analytics");
    expect(combined).not.toContain("не съдържа аналитични инструменти");
  });

  it("includes localized consent and admin analytics strings", () => {
    expect(en.cookieConsent.accept).toBe("Accept analytics");
    expect(bg.cookieConsent.accept).toBe("Приемам аналитика");
    expect(en.admin.analytics.navLabel).toBe("Analytics");
    expect(bg.admin.analytics.navLabel).toBe("Аналитика");
  });
});
