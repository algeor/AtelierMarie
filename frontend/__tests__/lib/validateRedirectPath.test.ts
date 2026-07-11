import { describe, it, expect } from "vitest";
import { validateRedirectPath } from "@/lib/validateRedirectPath";

describe("validateRedirectPath", () => {
  it("accepts valid relative paths", () => {
    expect(validateRedirectPath("/")).toBe("/");
    expect(validateRedirectPath("/products")).toBe("/products");
    expect(validateRedirectPath("/account")).toBe("/account");
    expect(validateRedirectPath("/orders/123")).toBe("/orders/123");
  });

  it("strips query strings and fragments", () => {
    expect(validateRedirectPath("/products?sort=price")).toBe("/products");
    expect(validateRedirectPath("/account#section")).toBe("/account");
    expect(validateRedirectPath("/orders?page=2#top")).toBe("/orders");
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

  it("rejects path traversal", () => {
    expect(validateRedirectPath("/../../etc/passwd")).toBe("/");
    expect(validateRedirectPath("/products/../admin")).toBe("/");
    expect(validateRedirectPath("/./hidden")).toBe("/");
  });

  it("rejects backslashes", () => {
    expect(validateRedirectPath("/foo\\bar")).toBe("/");
  });

  it("rejects control characters", () => {
    expect(validateRedirectPath("/foo\x00bar")).toBe("/");
    expect(validateRedirectPath("/foo\nbar")).toBe("/");
  });
});
