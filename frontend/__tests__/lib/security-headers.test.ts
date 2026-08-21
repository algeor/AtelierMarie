import { afterEach, describe, expect, it, vi } from "vitest";
import {
  buildContentSecurityPolicy,
  createCspNonce,
  CSP_HEADER,
  CSP_NONCE_HEADER,
  HSTS_HEADER,
  HSTS_HEADER_VALUE,
} from "@/lib/security-headers";

describe("security headers", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("defines a strong HSTS policy", () => {
    expect(CSP_HEADER).toBe("Content-Security-Policy");
    expect(CSP_NONCE_HEADER).toBe("x-nonce");
    expect(HSTS_HEADER).toBe("Strict-Transport-Security");
    expect(HSTS_HEADER_VALUE).toBe("max-age=31536000; includeSubDomains; preload");
  });

  it("creates a random base64 nonce", () => {
    const first = createCspNonce();
    const second = createCspNonce();

    expect(first).toMatch(/^[A-Za-z0-9+/]+=*$/);
    expect(first).not.toBe(second);
  });

  it("builds an enforcement CSP with a nonce and no unsafe inline scripts", () => {
    vi.stubEnv("NODE_ENV", "production");

    const policy = buildContentSecurityPolicy("test-nonce");

    expect(policy).toContain("default-src 'self'");
    expect(policy).toContain("object-src 'none'");
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).toContain("script-src 'self' 'nonce-test-nonce' 'strict-dynamic' https:");
    expect(policy).not.toMatch(/script-src[^;]*'unsafe-inline'/);
    expect(policy).not.toMatch(/script-src[^;]*'unsafe-eval'/);
    expect(policy).not.toMatch(/script-src[^;]*http:/);
    expect(policy).toContain("style-src-elem 'self' 'nonce-test-nonce'");
    expect(policy).toContain("style-src-attr 'unsafe-inline'");
    expect(policy).toContain("upgrade-insecure-requests");
  });

  it("keeps local development affordances out of production", () => {
    vi.stubEnv("NODE_ENV", "development");

    const policy = buildContentSecurityPolicy("test-nonce");

    expect(policy).toMatch(/script-src[^;]*http:/);
    expect(policy).toMatch(/script-src[^;]*'unsafe-eval'/);
    expect(policy).toContain("ws://localhost:*");
    expect(policy).toContain("ws://127.0.0.1:*");
    expect(policy).not.toContain("upgrade-insecure-requests");
  });

  it("allows configured API and media origins", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/v1");
    vi.stubEnv("NEXT_PUBLIC_MEDIA_URL", "https://cdn.example.com/static/");

    const policy = buildContentSecurityPolicy("test-nonce");

    expect(policy).toContain("connect-src 'self' https://api.example.com");
    expect(policy).toContain("img-src 'self' data: blob: https://cdn.example.com https://api.example.com https:");
    expect(policy).toContain("media-src 'self' blob: https://cdn.example.com https://api.example.com https:");
  });
});
