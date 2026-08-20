"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import type { FaqSectionResponse } from "@/lib/types";
import { FaqAccordion } from "./FaqAccordion";

interface FaqCategoryBrowserProps {
  sections: FaqSectionResponse[];
  categoryLabel: string;
}

export function FaqCategoryBrowser({
  sections,
  categoryLabel,
}: FaqCategoryBrowserProps) {
  const visibleSections = useMemo(
    () => sections.filter((section) => section.items.length > 0),
    [sections],
  );
  const [activeSlug, setActiveSlug] = useState(visibleSections[0]?.slug ?? "");
  const activeSection =
    visibleSections.find((section) => section.slug === activeSlug) ??
    visibleSections[0];
  const activeIndex = visibleSections.findIndex(
    (section) => section.slug === activeSection?.slug,
  );

  if (!activeSection) return null;

  return (
    <div className="space-y-7">
      <div className="relative -mx-4 sm:mx-0">
        <div className="pointer-events-none absolute inset-y-0 left-0 z-20 w-8 bg-gradient-to-r from-page to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-20 w-8 bg-gradient-to-l from-page to-transparent" />
        <div
          className="faq-category-rail overflow-x-auto px-4 pb-5 pt-5 sm:px-1"
          aria-label={categoryLabel}
        >
          <div className="flex min-w-max items-stretch pl-4 pr-6 sm:pl-5">
            {visibleSections.map((section, index) => {
              const active = section.slug === activeSection.slug;
              const stackLevel = active
                ? visibleSections.length + 10
                : visibleSections.length - Math.abs(index - activeIndex);
              return (
                <button
                  key={section.slug}
                  type="button"
                  aria-pressed={active}
                  aria-controls={`faq-section-${section.slug}`}
                  onClick={() => setActiveSlug(section.slug)}
                  className={cn(
                    "faq-category-card faq-category-card-enter relative -ml-8 inline-flex min-h-[82px] w-[12.25rem] flex-col items-start justify-between rounded-brand px-4 py-3 text-left text-sm transition-[transform,box-shadow,background-color,color,filter] duration-normal ease-brand first:ml-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page sm:-ml-10 sm:w-[13.75rem]",
                    active
                      ? "faq-category-card-active -translate-y-3 scale-[1.065] bg-text text-page shadow-2xl shadow-text/24 ring-2 ring-accent-soft/70"
                      : "bg-surface-elevated text-muted shadow-md shadow-border/10 ring-1 ring-border/25 brightness-[0.98] hover:-translate-y-1 hover:scale-[1.025] hover:bg-surface hover:text-text hover:shadow-xl hover:shadow-border/18",
                  )}
                  style={{
                    animationDelay: `${index * 55}ms`,
                    zIndex: stackLevel,
                  }}
                >
                  <span className="flex w-full items-center justify-between gap-3">
                    <span className="font-semibold leading-5">
                      {section.title}
                    </span>
                    {section.icon ? (
                      <span
                        aria-hidden="true"
                        className={cn(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-base",
                          active ? "bg-page/15" : "bg-page/70",
                        )}
                      >
                        {section.icon}
                      </span>
                    ) : null}
                  </span>
                  <span
                    className={cn(
                      "mt-3 h-1 rounded-full transition-[width,background-color] duration-normal ease-brand",
                      active ? "w-16 bg-accent-soft" : "w-10 bg-border/30",
                    )}
                  />
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <section
        key={activeSection.slug}
        id={activeSection.slug}
        className="scroll-mt-28"
        aria-labelledby={`faq-section-${activeSection.slug}-title`}
      >
        <div
          id={`faq-section-${activeSection.slug}`}
          className="mb-5 flex items-center gap-4"
        >
          {activeSection.icon ? (
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-surface-elevated/70 text-xl shadow-sm shadow-border/10">
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
            <div className="mt-2 h-px w-24 bg-accent/70" />
          </div>
        </div>
        <FaqAccordion
          key={activeSection.slug}
          items={activeSection.items}
          staggered
        />
      </section>
    </div>
  );
}
