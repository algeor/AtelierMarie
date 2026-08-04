import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

const globalsCss = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");
const tailwindConfig = readFileSync(join(process.cwd(), "tailwind.config.ts"), "utf8");

function flattenKeys(value: unknown, prefix = ""): string[] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [prefix];
  return Object.entries(value).flatMap(([key, child]) => flattenKeys(child, prefix ? `${prefix}.${key}` : key));
}

describe("rebrand system", () => {
  it("defines semantic color tokens and maps them through Tailwind", () => {
    for (const token of [
      "--color-page",
      "--color-surface",
      "--color-surface-elevated",
      "--color-text",
      "--color-muted",
      "--color-border",
      "--color-primary",
      "--color-accent",
      "--color-focus",
      "--color-success",
      "--color-warning",
      "--color-error",
      "--color-admin-page",
      "--color-admin-surface",
      "--color-admin-text",
    ]) {
      expect(globalsCss).toContain(token);
      expect(tailwindConfig).toContain(token);
    }
  });

  it("keeps decorative rebrand motion behind reduced-motion fallbacks", () => {
    expect(globalsCss).toContain("@media (prefers-reduced-motion: reduce)");
    expect(globalsCss).toContain(".signature-mark--reveal");
    expect(globalsCss).toContain(".rebrand-line-draw");
    expect(globalsCss).toContain(".rebrand-slow-reveal");
    expect(globalsCss).toContain(".rebrand-soft-panel-expand");
    expect(globalsCss).toContain(".rebrand-footer-wordmark-reveal");
  });

  it("keeps Bulgarian rebrand message keys in parity with English", () => {
    expect(flattenKeys(bgMessages).sort()).toEqual(flattenKeys(enMessages).sort());
  });
});
