"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import {
  getAdminSeoLandingPages,
  updateSeoLandingFaqItem,
  updateSeoLandingPage,
} from "@/lib/api";
import type { SeoLandingAdminResponse, SeoLandingFaqAdminResponse, SeoLandingPageAdminResponse } from "@/lib/types";

type PageField = keyof Omit<
  SeoLandingPageAdminResponse,
  | "slug"
  | "product_type"
  | "path_en"
  | "path_bg"
  | "created_at"
  | "updated_at"
  | "faq"
>;

type FaqField = keyof Pick<
  SeoLandingFaqAdminResponse,
  "question_en" | "question_bg" | "answer_en" | "answer_bg" | "is_published"
>;

function joinLines(lines: string[] | null): string {
  return lines?.join("\n") ?? "";
}

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function SeoPagesManager() {
  const searchParams = useSearchParams();
  const [data, setData] = useState<SeoLandingAdminResponse | null>(null);
  const [selectedSlug, setSelectedSlug] = useState("handmade-candles");
  const [benefitDrafts, setBenefitDrafts] = useState<Record<string, { en: string; bg: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function refresh() {
    const next = await getAdminSeoLandingPages();
    setData(next);
    setBenefitDrafts(
      Object.fromEntries(
        next.pages.map((page) => [
          page.slug,
          { en: joinLines(page.benefits_en), bg: joinLines(page.benefits_bg) },
        ]),
      ),
    );
  }

  useEffect(() => {
    refresh().catch((err) => {
      setError(err instanceof Error ? err.message : "Could not load SEO pages.");
    });
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  const page = useMemo(
    () => data?.pages.find((item) => item.slug === selectedSlug) ?? data?.pages[0] ?? null,
    [data, selectedSlug],
  );

  useEffect(() => {
    if (page && page.slug !== selectedSlug) setSelectedSlug(page.slug);
  }, [page, selectedSlug]);

  useEffect(() => {
    const requestedPage = searchParams?.get("page");
    if (requestedPage && data?.pages.some((item) => item.slug === requestedPage)) {
      setSelectedSlug(requestedPage);
    }
  }, [data, searchParams]);

  function showSaved() {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message: "Saved." }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function updatePageDraft(field: PageField, value: string | boolean | string[] | null) {
    setData((current) =>
      current
        ? {
            ...current,
            pages: current.pages.map((item) =>
              item.slug === selectedSlug ? { ...item, [field]: value } : item,
            ),
          }
        : current,
    );
  }

  function updateFaqDraft(itemId: number, field: FaqField, value: string | boolean | null) {
    setData((current) =>
      current
        ? {
            ...current,
            pages: current.pages.map((item) =>
              item.slug === selectedSlug
                ? {
                    ...item,
                    faq: item.faq.map((faq) =>
                      faq.id === itemId ? { ...faq, [field]: value } : faq,
                    ),
                  }
                : item,
            ),
          }
        : current,
    );
  }

  async function savePage() {
    if (!page) return;
    setBusyKey("page");
    setError(null);
    try {
      const drafts = benefitDrafts[page.slug] ?? { en: "", bg: "" };
      const updated = await updateSeoLandingPage(page.slug, {
        meta_title_en: page.meta_title_en,
        meta_title_bg: page.meta_title_bg || null,
        meta_description_en: page.meta_description_en,
        meta_description_bg: page.meta_description_bg || null,
        eyebrow_en: page.eyebrow_en,
        eyebrow_bg: page.eyebrow_bg || null,
        title_en: page.title_en,
        title_bg: page.title_bg || null,
        intro_en: page.intro_en,
        intro_bg: page.intro_bg || null,
        note_en: page.note_en,
        note_bg: page.note_bg || null,
        shop_all_label_en: page.shop_all_label_en,
        shop_all_label_bg: page.shop_all_label_bg || null,
        section_title_en: page.section_title_en,
        section_title_bg: page.section_title_bg || null,
        empty_text_en: page.empty_text_en,
        empty_text_bg: page.empty_text_bg || null,
        benefits_title_en: page.benefits_title_en,
        benefits_title_bg: page.benefits_title_bg || null,
        faq_title_en: page.faq_title_en,
        faq_title_bg: page.faq_title_bg || null,
        benefits_en: splitLines(drafts.en),
        benefits_bg: splitLines(drafts.bg),
        is_published: page.is_published,
      });
      setData((current) =>
        current
          ? {
              ...current,
              pages: current.pages.map((item) =>
                item.slug === updated.slug ? { ...updated, faq: item.faq } : item,
              ),
            }
          : current,
      );
      showSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save SEO page.");
    } finally {
      setBusyKey(null);
    }
  }

  async function saveFaq(item: SeoLandingFaqAdminResponse) {
    if (!page) return;
    setBusyKey(`faq-${item.id}`);
    setError(null);
    try {
      const updated = await updateSeoLandingFaqItem(page.slug, item.id, {
        question_en: item.question_en,
        question_bg: item.question_bg || null,
        answer_en: item.answer_en,
        answer_bg: item.answer_bg || null,
        is_published: item.is_published,
      });
      setData((current) =>
        current
          ? {
              ...current,
              pages: current.pages.map((candidate) =>
                candidate.slug === page.slug
                  ? {
                      ...candidate,
                      faq: candidate.faq.map((faq) => (faq.id === updated.id ? updated : faq)),
                    }
                  : candidate,
              ),
            }
          : current,
      );
      showSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save FAQ item.");
    } finally {
      setBusyKey(null);
    }
  }

  if (!page) {
    return <div className="rounded-brand border border-admin-border bg-admin-surface p-4 text-sm text-admin-muted">Loading SEO pages...</div>;
  }

  return (
    <div className="space-y-6">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">SEO landing pages</p>
            <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">Handmade candles</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-soft-brown">
              Edit the dedicated Google landing page copy, metadata, benefit bullets, and FAQ content.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={page.path_en} className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/40">
              View EN
            </Link>
            <Link href={page.path_bg} className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/40">
              View BG
            </Link>
          </div>
        </div>
      </header>

      {error ? <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {saveNotice ? <SaveConfirmation key={saveNotice.id} message={saveNotice.message} /> : null}

      <section className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-heading text-xl text-charcoal">Page copy</h2>
          <label className="flex items-center gap-2 text-sm text-soft-brown">
            <input
              type="checkbox"
              checked={page.is_published}
              onChange={(event) => updatePageDraft("is_published", event.target.checked)}
            />
            Published
          </label>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <TextField label="Meta title EN" value={page.meta_title_en} onChange={(value) => updatePageDraft("meta_title_en", value)} />
          <TextField label="Meta title BG" value={page.meta_title_bg ?? ""} onChange={(value) => updatePageDraft("meta_title_bg", value)} />
          <TextArea label="Meta description EN" value={page.meta_description_en} onChange={(value) => updatePageDraft("meta_description_en", value)} />
          <TextArea label="Meta description BG" value={page.meta_description_bg ?? ""} onChange={(value) => updatePageDraft("meta_description_bg", value)} />
          <TextField label="Eyebrow EN" value={page.eyebrow_en} onChange={(value) => updatePageDraft("eyebrow_en", value)} />
          <TextField label="Eyebrow BG" value={page.eyebrow_bg ?? ""} onChange={(value) => updatePageDraft("eyebrow_bg", value)} />
          <TextField label="H1 EN" value={page.title_en} onChange={(value) => updatePageDraft("title_en", value)} />
          <TextField label="H1 BG" value={page.title_bg ?? ""} onChange={(value) => updatePageDraft("title_bg", value)} />
          <TextArea label="Intro EN" value={page.intro_en} onChange={(value) => updatePageDraft("intro_en", value)} />
          <TextArea label="Intro BG" value={page.intro_bg ?? ""} onChange={(value) => updatePageDraft("intro_bg", value)} />
          <TextArea label="Custom note EN" value={page.note_en} onChange={(value) => updatePageDraft("note_en", value)} />
          <TextArea label="Custom note BG" value={page.note_bg ?? ""} onChange={(value) => updatePageDraft("note_bg", value)} />
          <TextField label="Product section title EN" value={page.section_title_en} onChange={(value) => updatePageDraft("section_title_en", value)} />
          <TextField label="Product section title BG" value={page.section_title_bg ?? ""} onChange={(value) => updatePageDraft("section_title_bg", value)} />
          <TextArea label="Empty state EN" value={page.empty_text_en} onChange={(value) => updatePageDraft("empty_text_en", value)} />
          <TextArea label="Empty state BG" value={page.empty_text_bg ?? ""} onChange={(value) => updatePageDraft("empty_text_bg", value)} />
          <TextField label="Button label EN" value={page.shop_all_label_en} onChange={(value) => updatePageDraft("shop_all_label_en", value)} />
          <TextField label="Button label BG" value={page.shop_all_label_bg ?? ""} onChange={(value) => updatePageDraft("shop_all_label_bg", value)} />
          <TextField label="Benefits title EN" value={page.benefits_title_en} onChange={(value) => updatePageDraft("benefits_title_en", value)} />
          <TextField label="Benefits title BG" value={page.benefits_title_bg ?? ""} onChange={(value) => updatePageDraft("benefits_title_bg", value)} />
          <TextField label="FAQ title EN" value={page.faq_title_en} onChange={(value) => updatePageDraft("faq_title_en", value)} />
          <TextField label="FAQ title BG" value={page.faq_title_bg ?? ""} onChange={(value) => updatePageDraft("faq_title_bg", value)} />
          <TextArea label="Benefits EN, one per line" value={benefitDrafts[page.slug]?.en ?? ""} onChange={(value) => setBenefitDrafts((current) => ({ ...current, [page.slug]: { ...(current[page.slug] ?? { en: "", bg: "" }), en: value } }))} />
          <TextArea label="Benefits BG, one per line" value={benefitDrafts[page.slug]?.bg ?? ""} onChange={(value) => setBenefitDrafts((current) => ({ ...current, [page.slug]: { ...(current[page.slug] ?? { en: "", bg: "" }), bg: value } }))} />
        </div>
        <div className="mt-5 flex justify-end">
          <Button onClick={savePage} disabled={busyKey === "page"}>{busyKey === "page" ? "Saving..." : "Save page"}</Button>
        </div>
      </section>

      <section className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <h2 className="font-heading text-xl text-charcoal">FAQ</h2>
        <div className="mt-4 space-y-4">
          {page.faq.map((item) => (
            <div key={item.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-charcoal">Question {item.sort_order + 1}</p>
                <label className="flex items-center gap-2 text-sm text-soft-brown">
                  <input type="checkbox" checked={item.is_published} onChange={(event) => updateFaqDraft(item.id, "is_published", event.target.checked)} />
                  Published
                </label>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <TextField label="Question EN" value={item.question_en} onChange={(value) => updateFaqDraft(item.id, "question_en", value)} />
                <TextField label="Question BG" value={item.question_bg ?? ""} onChange={(value) => updateFaqDraft(item.id, "question_bg", value)} />
                <TextArea label="Answer EN" value={item.answer_en} onChange={(value) => updateFaqDraft(item.id, "answer_en", value)} />
                <TextArea label="Answer BG" value={item.answer_bg ?? ""} onChange={(value) => updateFaqDraft(item.id, "answer_bg", value)} />
              </div>
              <div className="mt-4 flex justify-end">
                <Button onClick={() => saveFaq(item)} disabled={busyKey === `faq-${item.id}`}>{busyKey === `faq-${item.id}` ? "Saving..." : "Save question"}</Button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm text-charcoal focus:border-soft-brown focus:outline-none focus:ring-1 focus:ring-soft-brown" />
    </label>
  );
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea value={value} onChange={(event) => onChange(event.target.value)} rows={4} className="mt-1 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm leading-6 text-charcoal focus:border-soft-brown focus:outline-none focus:ring-1 focus:ring-soft-brown" />
    </label>
  );
}
