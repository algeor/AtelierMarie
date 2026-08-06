"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { getAdminPrivacy, updatePrivacyPage, updatePrivacySection } from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type {
  PrivacyAdminResponse,
  PrivacyPageAdminResponse,
  PrivacySectionAdminResponse,
} from "@/lib/types";

type PageField = keyof Omit<PrivacyPageAdminResponse, "id" | "created_at" | "updated_at">;
type SectionTextField = "title_en" | "title_bg" | "nav_en" | "nav_bg";
type SectionDraft = { body_en: string; body_bg: string };
type Target = "page" | string;

const EMPTY_DRAFT: SectionDraft = { body_en: "", body_bg: "" };

function joinParagraphs(lines: string[] | null): string {
  return lines?.join("\n\n") ?? "";
}

function splitParagraphs(value: string): string[] {
  return value
    .split(/\n\s*\n/g)
    .map((line) => line.trim())
    .filter(Boolean);
}

function sectionDraft(section: PrivacySectionAdminResponse): SectionDraft {
  return { body_en: joinParagraphs(section.body_en), body_bg: joinParagraphs(section.body_bg) };
}

export function PrivacyManager() {
  const t = useTranslations("admin.privacy");
  const tCommon = useTranslations("common");
  const [privacy, setPrivacy] = useState<PrivacyAdminResponse | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<Target>("page");
  const [drafts, setDrafts] = useState<Record<string, SectionDraft>>({});
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAdminPrivacy()
      .then((data) => {
        if (cancelled) return;
        setPrivacy(data);
        setDrafts(Object.fromEntries(data.sections.map((section) => [section.slug, sectionDraft(section)])));
      })
      .catch(() => {
        if (!cancelled) setError(t("loadError"));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!privacy || selectedTarget === "page") return;
    if (!privacy.sections.some((section) => section.slug === selectedTarget)) {
      setSelectedTarget("page");
    }
  }, [privacy, selectedTarget]);

  const selectedSection = selectedTarget === "page" ? null : privacy?.sections.find((section) => section.slug === selectedTarget) ?? null;
  const overview = useMemo(() => summarizePrivacy(privacy, drafts), [privacy, drafts]);

  function showSaved(message = tCommon("saved")) {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function updatePageField(field: PageField, value: string) {
    setPrivacy((current) => current ? { ...current, page: { ...current.page, [field]: value } } : current);
  }

  function updateSectionField(slug: string, field: SectionTextField, value: string) {
    setPrivacy((current) =>
      current
        ? {
            ...current,
            sections: current.sections.map((section) => section.slug === slug ? { ...section, [field]: value } : section),
          }
        : current
    );
  }

  function updateDraft(slug: string, field: keyof SectionDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [slug]: { ...(current[slug] ?? EMPTY_DRAFT), [field]: value },
    }));
  }

  async function savePage() {
    if (!privacy) return;
    setError(null);
    try {
      const page = await updatePrivacyPage({
        meta_title_en: privacy.page.meta_title_en,
        meta_title_bg: privacy.page.meta_title_bg || null,
        meta_description_en: privacy.page.meta_description_en,
        meta_description_bg: privacy.page.meta_description_bg || null,
        eyebrow_en: privacy.page.eyebrow_en,
        eyebrow_bg: privacy.page.eyebrow_bg || null,
        title_en: privacy.page.title_en,
        title_bg: privacy.page.title_bg || null,
        subtitle_en: privacy.page.subtitle_en,
        subtitle_bg: privacy.page.subtitle_bg || null,
        last_updated_en: privacy.page.last_updated_en,
        last_updated_bg: privacy.page.last_updated_bg || null,
        controller_title_en: privacy.page.controller_title_en,
        controller_title_bg: privacy.page.controller_title_bg || null,
      });
      setPrivacy((current) => (current ? { ...current, page } : current));
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function saveSection(section: PrivacySectionAdminResponse) {
    const draft = drafts[section.slug] ?? sectionDraft(section);
    setError(null);
    try {
      const updated = await updatePrivacySection(section.slug, {
        title_en: section.title_en,
        title_bg: section.title_bg || null,
        nav_en: section.nav_en,
        nav_bg: section.nav_bg || null,
        body_en: splitParagraphs(draft.body_en),
        body_bg: splitParagraphs(draft.body_bg),
      });
      setPrivacy((current) =>
        current
          ? {
              ...current,
              sections: current.sections.map((candidate) => candidate.slug === updated.slug ? updated : candidate),
            }
          : current
      );
      setDrafts((current) => ({ ...current, [updated.slug]: sectionDraft(updated) }));
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  if (!privacy && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="space-y-5">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">Legal copy workspace</p>
          <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
          <p className="mt-1 text-sm leading-6 text-soft-brown">{t("subtitle")}</p>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewTile label="Sections" value={String(overview.sections)} detail="privacy blocks" />
          <OverviewTile label="Paragraphs" value={String(overview.paragraphs)} detail="public copy" />
          <OverviewTile label="Controller" value={overview.hasControllerTitle ? "Set" : "Missing"} detail="page detail" warning={!overview.hasControllerTitle} />
          <OverviewTile label="Translation gaps" value={String(overview.translationGaps)} detail="need review" warning={overview.translationGaps > 0} />
        </div>
      </header>

      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {privacy ? (
        <div className="grid gap-5 xl:grid-cols-[21rem_minmax(0,1fr)]">
          <aside className="space-y-3 xl:sticky xl:top-24 xl:self-start">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-heading text-xl font-semibold text-charcoal">Edit target</h2>
              <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{privacy.sections.length + 1} total</span>
            </div>
            <div className="space-y-2">
              <TargetCard
                title={t("pageSection")}
                detail={privacy.page.title_en}
                selected={selectedTarget === "page"}
                countLabel="Page fields"
                gaps={pageTranslationGapCount(privacy.page)}
                onSelect={() => setSelectedTarget("page")}
              />
              {privacy.sections.map((section) => (
                <TargetCard
                  key={section.slug}
                  title={section.title_en}
                  detail={section.slug}
                  selected={selectedTarget === section.slug}
                  countLabel={`${section.body_en.length} paragraph${section.body_en.length === 1 ? "" : "s"}`}
                  gaps={sectionTranslationGapCount(section, drafts[section.slug] ?? sectionDraft(section))}
                  onSelect={() => setSelectedTarget(section.slug)}
                />
              ))}
            </div>
          </aside>

          <section className="rounded-brand border border-admin-border/50 bg-admin-surface shadow-sm">
            {selectedTarget === "page" ? (
              <PageEditor page={privacy.page} onChange={updatePageField} onSave={savePage} />
            ) : selectedSection ? (
              <SectionEditor
                section={selectedSection}
                draft={drafts[selectedSection.slug] ?? sectionDraft(selectedSection)}
                onSectionChange={(field, value) => updateSectionField(selectedSection.slug, field, value)}
                onDraftChange={(field, value) => updateDraft(selectedSection.slug, field, value)}
                onSave={() => saveSection(selectedSection)}
              />
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  );
}

function PageEditor({ page, onChange, onSave }: { page: PrivacyPageAdminResponse; onChange: (field: PageField, value: string) => void; onSave: () => void }) {
  const t = useTranslations("admin.privacy");
  return (
    <div>
      <EditorHeader title={t("pageSection")} detail="SEO, hero, date, and controller labels for the public privacy page." />
      <div className="space-y-5 p-4 sm:p-5">
        <div className="grid gap-5 lg:grid-cols-2">
          <LanguagePanel title={t("english")}>
            <PageFields page={page} suffix="en" onChange={onChange} />
          </LanguagePanel>
          <LanguagePanel title={t("bulgarian")}>
            <PageFields page={page} suffix="bg" onChange={onChange} />
          </LanguagePanel>
        </div>
        <StickyActions>
          <Button type="button" onClick={onSave}>{t("savePage")}</Button>
        </StickyActions>
      </div>
    </div>
  );
}

function SectionEditor({ section, draft, onSectionChange, onDraftChange, onSave }: {
  section: PrivacySectionAdminResponse;
  draft: SectionDraft;
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
  onSave: () => void;
}) {
  const t = useTranslations("admin.privacy");
  return (
    <div>
      <EditorHeader title={section.title_en} detail={`${section.slug} · ${section.body_en.length} paragraph${section.body_en.length === 1 ? "" : "s"}`} />
      <div className="space-y-5 p-4 sm:p-5">
        <div className="grid gap-5 lg:grid-cols-2">
          <LanguagePanel title={t("english")}>
            <SectionFields section={section} draft={draft} suffix="en" onSectionChange={onSectionChange} onDraftChange={onDraftChange} />
          </LanguagePanel>
          <LanguagePanel title={t("bulgarian")}>
            <SectionFields section={section} draft={draft} suffix="bg" onSectionChange={onSectionChange} onDraftChange={onDraftChange} />
          </LanguagePanel>
        </div>
        <StickyActions>
          <Button type="button" onClick={onSave}>{t("saveSection")}</Button>
        </StickyActions>
      </div>
    </div>
  );
}

function EditorHeader({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="border-b border-admin-border/40 p-4 sm:p-5">
      <h2 className="font-heading text-2xl font-semibold text-charcoal">{title}</h2>
      <p className="mt-1 text-sm leading-6 text-soft-brown">{detail}</p>
    </div>
  );
}

function TargetCard({ title, detail, selected, countLabel, gaps, onSelect }: { title: string; detail: string; selected: boolean; countLabel: string; gaps: number; onSelect: () => void }) {
  return (
    <article className={cn("rounded-brand border bg-admin-surface p-3 transition-colors", selected ? "border-admin-primary shadow-md" : "border-admin-border/45 hover:border-admin-accent")}>
      <button type="button" onClick={onSelect} className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface" aria-current={selected ? "true" : undefined}>
        <h3 className="truncate font-heading text-lg text-charcoal">{title}</h3>
        <p className="mt-0.5 truncate text-xs text-soft-brown">{detail}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="rounded-pill border border-champagne-beige bg-warm-ivory px-2 py-1 text-xs font-semibold text-soft-brown">{countLabel}</span>
          {gaps > 0 ? <GapBadge count={gaps} /> : <span className="rounded-pill border border-green-200 bg-green-50 px-2 py-1 text-xs font-semibold text-green-700">EN/BG ready</span>}
        </div>
      </button>
    </article>
  );
}

function OverviewTile({ label, value, detail, warning = false }: { label: string; value: string; detail: string; warning?: boolean }) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-soft-brown">{label}</p>
      <div className="mt-1 flex items-end gap-2">
        <span className={cn("font-heading text-2xl font-semibold", warning ? "text-amber-700" : "text-charcoal")}>{value}</span>
        <span className="pb-1 text-xs text-soft-brown">{detail}</span>
      </div>
    </div>
  );
}

function GapBadge({ count }: { count: number }) {
  return <span className="rounded-pill border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">{count} BG gap{count === 1 ? "" : "s"}</span>;
}

function StickyActions({ children }: { children: ReactNode }) {
  return <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-brand border border-admin-border/50 bg-admin-surface/95 p-3 shadow-lg backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">{children}</div>;
}

function LanguagePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-4 rounded-brand border border-champagne-beige bg-warm-ivory p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-gold">{title}</h3>
      {children}
    </div>
  );
}

function PageFields({ page, suffix, onChange }: { page: PrivacyPageAdminResponse; suffix: "en" | "bg"; onChange: (field: PageField, value: string) => void }) {
  const t = useTranslations("admin.privacy");
  const field = (name: string) => `${name}_${suffix}` as PageField;
  return (
    <div className="space-y-3">
      <TextInput label={t("metaTitle")} value={String(page[field("meta_title")] ?? "")} onChange={(value) => onChange(field("meta_title"), value)} />
      <TextArea label={t("metaDescription")} rows={3} value={String(page[field("meta_description")] ?? "")} onChange={(value) => onChange(field("meta_description"), value)} />
      <TextInput label={t("eyebrow")} value={String(page[field("eyebrow")] ?? "")} onChange={(value) => onChange(field("eyebrow"), value)} />
      <TextInput label={t("pageTitle")} value={String(page[field("title")] ?? "")} onChange={(value) => onChange(field("title"), value)} />
      <TextArea label={t("subtitleField")} rows={3} value={String(page[field("subtitle")] ?? "")} onChange={(value) => onChange(field("subtitle"), value)} />
      <TextInput label={t("lastUpdated")} value={String(page[field("last_updated")] ?? "")} onChange={(value) => onChange(field("last_updated"), value)} />
      <TextInput label={t("controllerTitle")} value={String(page[field("controller_title")] ?? "")} onChange={(value) => onChange(field("controller_title"), value)} />
    </div>
  );
}

function SectionFields({ section, draft, suffix, onSectionChange, onDraftChange }: {
  section: PrivacySectionAdminResponse;
  draft: SectionDraft;
  suffix: "en" | "bg";
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
}) {
  const t = useTranslations("admin.privacy");
  const titleField = `title_${suffix}` as SectionTextField;
  const navField = `nav_${suffix}` as SectionTextField;
  const bodyField = `body_${suffix}` as keyof SectionDraft;
  return (
    <div className="space-y-3">
      <TextInput label={t("sectionTitle")} value={String(section[titleField] ?? "")} onChange={(value) => onSectionChange(titleField, value)} />
      <TextInput label={t("sectionNav")} value={String(section[navField] ?? "")} onChange={(value) => onSectionChange(navField, value)} />
      <TextArea label={t("body")} rows={8} value={draft[bodyField]} onChange={(value) => onDraftChange(bodyField, value)} />
    </div>
  );
}

function TextInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" />
    </label>
  );
}

function TextArea({ label, value, rows, onChange }: { label: string; value: string; rows: number; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea value={value} rows={rows} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" />
    </label>
  );
}

function summarizePrivacy(privacy: PrivacyAdminResponse | null, drafts: Record<string, SectionDraft>) {
  const sections = privacy?.sections ?? [];
  return {
    sections: sections.length,
    paragraphs: sections.reduce((total, section) => total + (drafts[section.slug]?.body_en ? splitParagraphs(drafts[section.slug]!.body_en).length : section.body_en.length), 0),
    hasControllerTitle: Boolean(privacy?.page.controller_title_en.trim()),
    translationGaps: (privacy ? pageTranslationGapCount(privacy.page) : 0) + sections.reduce((total, section) => total + sectionTranslationGapCount(section, drafts[section.slug] ?? sectionDraft(section)), 0),
  };
}

function pageTranslationGapCount(page: PrivacyPageAdminResponse) {
  const pairs: Array<[string | null | undefined, string | null | undefined]> = [
    [page.meta_title_en, page.meta_title_bg],
    [page.meta_description_en, page.meta_description_bg],
    [page.eyebrow_en, page.eyebrow_bg],
    [page.title_en, page.title_bg],
    [page.subtitle_en, page.subtitle_bg],
    [page.last_updated_en, page.last_updated_bg],
    [page.controller_title_en, page.controller_title_bg],
  ];
  return pairs.filter(([en, bg]) => !isBlank(en) && isBlank(bg)).length;
}

function sectionTranslationGapCount(section: PrivacySectionAdminResponse, draft: SectionDraft) {
  const pairs: Array<[string | null | undefined, string | null | undefined]> = [
    [section.title_en, section.title_bg],
    [section.nav_en, section.nav_bg],
    [draft.body_en, draft.body_bg],
  ];
  return pairs.filter(([en, bg]) => !isBlank(en) && isBlank(bg)).length;
}

function isBlank(value: string | null | undefined) {
  return !value || value.trim().length === 0;
}
