import { describe, it, expect } from "vitest";
import { validateRedirectPath } from "@/lib/validateRedirectPath";

describe("validateRedirectPath", () => {
  it("accepts valid relative paths", () => {
    expect(validateRedirectPath("/")).toBe("/");
    expect(validateRedirectPath("/products")).toBe("/products");
    expect(validateRedirectPath("/account")).toBe("/account");
    expect(validateRedirectPath("/orders/123")).toBe("/orders/123");
    expect(validateRedirectPath("/products?sort=price")).toBe("/products?sort=price");
  });

  it("rejects protocol-relative URLs", () => {
    expect(validateRedirectPath("//evil.com")).toBe("/");
    expect(validateRedirectPath("//evil.com/path")).toBe("/");
  });

  it("rejects absolute URLs", () => {
    expect(validateRedirectPath("https://evil.com")).toBe("/");
    expect(validateRedirectPath("http://evil.com/path")).toBe("/");
    expect(validateRedirectPath("ftp://evil.com")).toBe("/");
  });

  it("rejects javascript: URIs", () => {
    expect(validateRedirectPath("javascript:alert(1)")).toBe("/");
  });

  it("returns / for empty string", () => {
    expect(validateRedirectPath("")).toBe("/");
  });

  it("returns / for paths without leading slash", () => {
    expect(validateRedirectPath("products")).toBe("/");
    expect(validateRedirectPath("evil.com")).toBe("/");
  });
});
