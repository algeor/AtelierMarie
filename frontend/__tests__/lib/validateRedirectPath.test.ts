import { describe, it, expect } from "vitest";
import { validateRedirectPath } from "@/lib/validateRedirectPath";

describe("validateRedirectPath", () => {
  it("accepts valid relative paths", () => {
    expect(validateRedirectPath("/products")).toBe("/products");
    expect(validateRedirectPath("/account")).toBe("/account");
    expect(validateRedirectPath("/orders/123")).toBe("/orders/123");
    expect(validateRedirectPath("/")).toBe("/");
    expect(validateRedirectPath("/products?page=2")).toBe("/products?page=2");
  });

  it("rejects protocol-relative URLs", () => {
    expect(validateRedirectPath("//evil.com")).toBe("/");
    expect(validateRedirectPath("//evil.com/path")).toBe("/");
  });

  it("rejects absolute URLs", () => {
    expect(validateRedirectPath("https://evil.com")).toBe("/");
    expect(validateRedirectPath("http://evil.com/path")).toBe("/");
  });

  it("rejects javascript: URIs", () => {
    expect(validateRedirectPath("javascript:alert(1)")).toBe("/");
  });

  it("rejects empty string", () => {
    expect(validateRedirectPath("")).toBe("/");
  });

  it("rejects paths not starting with /", () => {
    expect(validateRedirectPath("products")).toBe("/");
    expect(validateRedirectPath("../etc/passwd")).toBe("/");
  });

  it("returns / as fallback for all invalid paths", () => {
    expect(validateRedirectPath("data:text/html,<script>")).toBe("/");
    expect(validateRedirectPath("  /products")).toBe("/");
  });
});
