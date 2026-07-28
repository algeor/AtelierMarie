"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { FaqItemResponse } from "@/lib/types";

interface FaqAccordionProps {
  items: FaqItemResponse[];
}

type AnswerBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

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

function Answer({ answer }: { answer: string }) {
  const blocks = parseFaqAnswer(answer);

  return (
    <div className="space-y-3 text-sm leading-7 text-soft-brown sm:text-base">
      {blocks.map((block, index) =>
        block.type === "list" ? (
          <ul key={index} className="list-disc space-y-2 pl-5">
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex}>{item}</li>
            ))}
          </ul>
        ) : (
          <p key={index}>{block.text}</p>
        )
      )}
    </div>
  );
}

export function FaqAccordion({ items }: FaqAccordionProps) {
  const [openId, setOpenId] = useState<number | null>(items[0]?.id ?? null);

  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const isOpen = openId === item.id;
        const panelId = `faq-panel-${item.id}`;
        const buttonId = `faq-trigger-${item.id}`;
        return (
          <div
            key={item.id}
            className="overflow-hidden rounded-2xl border border-champagne-beige bg-white shadow-sm"
          >
            <button
              id={buttonId}
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => setOpenId(isOpen ? null : item.id)}
              className="flex min-h-[56px] w-full items-center justify-between gap-4 px-5 py-4 text-left text-charcoal transition-colors duration-normal hover:bg-warm-ivory focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold focus-visible:ring-offset-2 focus-visible:ring-offset-white"
            >
              <span className="text-base font-medium leading-6">{item.question}</span>
              <span
                aria-hidden="true"
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-champagne-beige text-lg text-soft-brown transition-transform duration-normal",
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
                <div className="border-t border-champagne-beige px-5 py-5">
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
