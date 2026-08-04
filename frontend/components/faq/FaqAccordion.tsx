"use client";

import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { FaqItemResponse } from "@/lib/types";

interface FaqAccordionProps {
  items: FaqItemResponse[];
  staggered?: boolean;
}

type AnswerBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

const MARKDOWN_LINK_RE = /\[([^\]]+)\]\((\/[^)\s]+)\)/g;

export function parseFaqAnswer(answer: string): AnswerBlock[] {
  const blocks: AnswerBlock[] = [];
  let paragraph: string[] = [];
  let bullets: string[] = [];

  function flushParagraph() {
    if (paragraph.length === 0) return;
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    paragraph = [];
  }

  function flushBullets() {
    if (bullets.length === 0) return;
    blocks.push({ type: "list", items: bullets });
    bullets = [];
  }

  for (const rawLine of answer.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushBullets();
      continue;
    }
    if (line.startsWith("* ") || line.startsWith("- ")) {
      flushParagraph();
      bullets.push(line.slice(2).trim());
      continue;
    }
    flushBullets();
    paragraph.push(line);
  }

  flushParagraph();
  flushBullets();
  return blocks;
}

function renderTextWithLinks(text: string) {
  const parts: ReactNode[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(MARKDOWN_LINK_RE)) {
    const [fullMatch, label, href] = match;
    const start = match.index ?? 0;

    if (start > lastIndex) {
      parts.push(text.slice(lastIndex, start));
    }

    parts.push(
      <a
        key={`${href}-${start}`}
        href={href}
        className="font-medium text-text underline underline-offset-4 hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        {label}
      </a>
    );
    lastIndex = start + fullMatch.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

function Answer({ answer }: { answer: string }) {
  const blocks = parseFaqAnswer(answer);

  return (
    <div className="space-y-3 text-sm leading-7 text-muted sm:text-base">
      {blocks.map((block, index) =>
        block.type === "list" ? (
          <ul key={index} className="list-disc space-y-2 pl-5">
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex}>{renderTextWithLinks(item)}</li>
            ))}
          </ul>
        ) : (
          <p key={index}>{renderTextWithLinks(block.text)}</p>
        )
      )}
    </div>
  );
}

export function FaqAccordion({ items, staggered = false }: FaqAccordionProps) {
  const [openId, setOpenId] = useState<number | null>(null);

  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const isOpen = openId === item.id;
        const panelId = `faq-panel-${item.id}`;
        const buttonId = `faq-trigger-${item.id}`;
        return (
          <div
            key={item.id}
            className={cn(
              "overflow-hidden rounded-brand border border-border/60 bg-surface-elevated shadow-sm shadow-border/10",
              staggered && "rebrand-soft-panel-expand"
            )}
            style={staggered ? { animationDelay: `${index * 75}ms` } : undefined}
          >
            <button
              id={buttonId}
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => setOpenId(isOpen ? null : item.id)}
              className="flex min-h-[56px] w-full items-center justify-between gap-4 px-5 py-4 text-left text-text transition-colors duration-normal hover:bg-page focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-surface-elevated"
            >
              <span className="text-base font-medium leading-6">{item.question}</span>
              <span
                aria-hidden="true"
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border text-lg text-muted transition-transform duration-normal",
                  isOpen && "rotate-45"
                )}
              >
                +
              </span>
            </button>
            <div
              id={panelId}
              role="region"
              aria-labelledby={buttonId}
              className={cn(
                "grid transition-[grid-template-rows,opacity] duration-normal ease-out",
                isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
              )}
            >
              <div className="overflow-hidden">
                <div className="border-t border-border/60 bg-page/40 px-5 py-5">
                  <Answer answer={item.answer} />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
