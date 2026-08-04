"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import type { FaqSectionResponse } from "@/lib/types";
import { FaqAccordion } from "./FaqAccordion";

interface FaqCategoryBrowserProps {
  sections: FaqSectionResponse[];
  categoryLabel: string;
}

export function FaqCategoryBrowser({ sections, categoryLabel }: FaqCategoryBrowserProps) {
  const visibleSections = useMemo(
    () => sections.filter((section) => section.items.length > 0),
    [sections]
  );
  const [activeSlug, setActiveSlug] = useState(visibleSections[0]?.slug ?? "");
  const activeSection = visibleSections.find((section) => section.slug === activeSlug) ?? visibleSections[0];

  if (!activeSection) return null;

  return (
    <div className="space-y-7">
      <div className="-mx-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0" aria-label={categoryLabel}>
        <div className="flex min-w-max gap-2">
          {visibleSections.map((section) => {
            const active = section.slug === activeSection.slug;
            return (
              <button
                key={section.slug}
                type="button"
                aria-pressed={active}
                aria-controls={`faq-section-${section.slug}`}
                onClick={() => setActiveSlug(section.slug)}
                className={cn(
                  "inline-flex min-h-[44px] items-center gap-2 rounded-brand border px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page",
                  active
                    ? "border-accent bg-accent text-accent-foreground"
                    : "border-border/70 bg-surface-elevated text-muted hover:bg-surface hover:text-text"
                )}
              >
                {section.icon ? <span aria-hidden="true">{section.icon}</span> : null}
                <span>{section.title}</span>
              </button>
            );
          })}
        </div>
      </div>

      <section
        key={activeSection.slug}
        id={activeSection.slug}
        className="scroll-mt-28"
        aria-labelledby={`faq-section-${activeSection.slug}-title`}
      >
        <div id={`faq-section-${activeSection.slug}`} className="mb-5 flex items-center gap-4">
          {activeSection.icon ? (
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-surface-elevated text-xl shadow-sm shadow-border/10">
              {activeSection.icon}
            </span>
          ) : null}
          <div>
            <h2
              id={`faq-section-${activeSection.slug}-title`}
              className="font-heading text-2xl text-text sm:text-3xl"
            >
              {activeSection.title}
            </h2>
            <div className="mt-2 h-0.5 w-20 bg-accent" />
          </div>
        </div>
        <FaqAccordion key={activeSection.slug} items={activeSection.items} staggered />
      </section>
    </div>
  );
}
