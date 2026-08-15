"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { AdminMobileTargetSelect } from "@/components/admin/AdminMobileTargetSelect";
import { AdminTranslationGapButton, MissingBgLabel, isMissingTranslation, type AdminTranslationGap } from "@/components/admin/AdminTranslationGaps";
import { getAdminTerms, updateTermsPage, updateTermsSection } from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type {
  TermsAdminResponse,
  TermsPageAdminResponse,
  TermsSectionAdminResponse,
} from "@/lib/types";

type PageField = keyof Omit<TermsPageAdminResponse, "id" | "created_at" | "updated_at">;

type SectionTextField =
  | "title_en"
  | "title_bg"
  | "nav_en"
  | "nav_bg"
  | "model_form_title_en"
  | "model_form_title_bg"
  | "model_form_intro_en"
  | "model_form_intro_bg";

type SectionDraft = {
  body_en: string;
  body_bg: string;
  model_form_lines_en: string;
  model_form_lines_bg: string;
};

type Target = "page" | string;

const EMPTY_SECTION_DRAFT: SectionDraft = {
  body_en: "",
  body_bg: "",
  model_form_lines_en: "",
  model_form_lines_bg: "",
};

function joinParagraphs(lines: string[] | null): string {
  return lines?.join("\n\n") ?? "";
}

function joinLines(lines: string[] | null): string {
  return lines?.join("\n") ?? "";
}

function splitParagraphs(value: string): string[] {
  return value
    .split(/\n\s*\n/g)
    .map((line) => line.trim())
    .filter(Boolean);
}

function splitLines(value: string): string[] | null {
  const lines = value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.length > 0 ? lines : null;
}

function sectionDraft(section: TermsSectionAdminResponse): SectionDraft {
  return {
    body_en: joinParagraphs(section.body_en),
    body_bg: joinParagraphs(section.body_bg),
    model_form_lines_en: joinLines(section.model_form_lines_en),
    model_form_lines_bg: joinLines(section.model_form_lines_bg),
  };
}

export function TermsManager() {
  const t = useTranslations("admin.terms");
  const tCommon = useTranslations("common");
  const searchParams = useSearchParams();
  const [terms, setTerms] = useState<TermsAdminResponse | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<Target>("page");
  const [drafts, setDrafts] = useState<Record<string, SectionDraft>>({});
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAdminTerms()
      .then((data) => {
        if (cancelled) return;
        setTerms(data);
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
    if (!terms) return;
    const requestedTarget = searchParams?.get("target") ?? null;
    if (requestedTarget && (requestedTarget === "page" || terms.sections.some((section) => section.slug === requestedTarget))) {
      setSelectedTarget(requestedTarget);
      return;
    }
    if (selectedTarget !== "page" && !terms.sections.some((section) => section.slug === selectedTarget)) {
      setSelectedTarget("page");
    }
  }, [terms, selectedTarget, searchParams]);

  const selectedSection = selectedTarget === "page" ? null : terms?.sections.find((section) => section.slug === selectedTarget) ?? null;
  const overview = useMemo(() => summarizeTerms(terms, drafts), [terms, drafts]);
  const allTranslationGaps = terms ? [
    ...termsPageTranslationGaps(terms.page, () => setSelectedTarget("page")),
    ...terms.sections.flatMap((section) => termsSectionTranslationGaps(section, drafts[section.slug] ?? sectionDraft(section), () => setSelectedTarget(section.slug))),
  ] : [];
  const mobileTargetOptions = terms ? [
    {
      value: "page",
      label: t("pageSection"),
      group: "Page",
      description: "SEO, hero, policy links, and navigation labels",
    },
    ...terms.sections.map((section) => {
      const draft = drafts[section.slug] ?? sectionDraft(section);
      const paragraphs = splitParagraphs(draft.body_en).length;
      const formLines = splitLines(draft.model_form_lines_en)?.length ?? 0;
      return {
        value: section.slug,
        label: section.title_en,
        group: "Terms sections",
        description: `${paragraphs} paragraph${paragraphs === 1 ? "" : "s"}${formLines > 0 ? ` · ${formLines} form line${formLines === 1 ? "" : "s"}` : ""}`,
      };
    }),
  ] : [];

  function showSaved(message = tCommon("saved")) {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function updatePageField(field: PageField, value: string) {
    setTerms((current) => current ? { ...current, page: { ...current.page, [field]: value } } : current);
  }

  function updateSectionField(slug: string, field: SectionTextField, value: string) {
    setTerms((current) =>
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
      [slug]: { ...(current[slug] ?? EMPTY_SECTION_DRAFT), [field]: value },
    }));
  }

  async function savePage() {
    if (!terms) return;
    setError(null);
    try {
      const page = await updateTermsPage({
        meta_title_en: terms.page.meta_title_en,
        meta_title_bg: terms.page.meta_title_bg || null,
        meta_description_en: terms.page.meta_description_en,
        meta_description_bg: terms.page.meta_description_bg || null,
        eyebrow_en: terms.page.eyebrow_en,
        eyebrow_bg: terms.page.eyebrow_bg || null,
        title_en: terms.page.title_en,
        title_bg: terms.page.title_bg || null,
        subtitle_en: terms.page.subtitle_en,
        subtitle_bg: terms.page.subtitle_bg || null,
        last_updated_en: terms.page.last_updated_en,
        last_updated_bg: terms.page.last_updated_bg || null,
        identity_intro_en: terms.page.identity_intro_en,
        identity_intro_bg: terms.page.identity_intro_bg || null,
        policy_links_title_en: terms.page.policy_links_title_en,
        policy_links_title_bg: terms.page.policy_links_title_bg || null,
        privacy_link_en: terms.page.privacy_link_en,
        privacy_link_bg: terms.page.privacy_link_bg || null,
        cookies_link_en: terms.page.cookies_link_en,
        cookies_link_bg: terms.page.cookies_link_bg || null,
        nav_label_en: terms.page.nav_label_en,
        nav_label_bg: terms.page.nav_label_bg || null,
        back_to_top_en: terms.page.back_to_top_en,
        back_to_top_bg: terms.page.back_to_top_bg || null,
      });
      setTerms((current) => (current ? { ...current, page } : current));
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function saveSection(section: TermsSectionAdminResponse) {
    const draft = drafts[section.slug] ?? sectionDraft(section);
    setError(null);
    try {
      const updated = await updateTermsSection(section.slug, {
        title_en: section.title_en,
        title_bg: section.title_bg || null,
        nav_en: section.nav_en,
        nav_bg: section.nav_bg || null,
        body_en: splitParagraphs(draft.body_en),
        body_bg: splitParagraphs(draft.body_bg),
        model_form_title_en: section.model_form_title_en || null,
        model_form_title_bg: section.model_form_title_bg || null,
        model_form_intro_en: section.model_form_intro_en || null,
        model_form_intro_bg: section.model_form_intro_bg || null,
        model_form_lines_en: splitLines(draft.model_form_lines_en),
        model_form_lines_bg: splitLines(draft.model_form_lines_bg),
      });
      setTerms((current) =>
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

  if (!terms && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="min-w-0 space-y-5">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">Legal copy workspace</p>
          <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
          <p className="mt-1 text-sm leading-6 text-soft-brown">{t("subtitle")}</p>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewTile label="Sections" value={String(overview.sections)} detail="legal blocks" />
          <OverviewTile label="Paragraphs" value={String(overview.paragraphs)} detail="public copy" />
          <OverviewTile label="Form lines" value={String(overview.formLines)} detail="withdrawal form" />
          <OverviewTile label="Translation gaps" value={<AdminTranslationGapButton gaps={allTranslationGaps} label="Terms translation gaps" />} detail="need review" warning={overview.translationGaps > 0} />
        </div>
      </header>

      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {terms ? (
        <div className="grid min-w-0 gap-5 xl:grid-cols-[21rem_minmax(0,1fr)]">
          <AdminMobileTargetSelect
            label="Edit target"
            value={selectedTarget}
            onChange={(value) => setSelectedTarget(value)}
            options={mobileTargetOptions}
          />

          <aside className="hidden min-w-0 space-y-3 xl:sticky xl:top-24 xl:block xl:self-start">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-heading text-xl font-semibold text-charcoal">Edit target</h2>
              <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{terms.sections.length + 1} total</span>
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <MenuGroupLabel>Page</MenuGroupLabel>
                <TargetCard
                  title={t("pageSection")}
                  detail={terms.page.title_en}
                  selected={selectedTarget === "page"}
                  countLabel="SEO, hero, links"
                  gaps={termsPageTranslationGaps(terms.page, () => setSelectedTarget("page"))}
                  onSelect={() => setSelectedTarget("page")}
                />
              </div>

              <div className="space-y-2">
                <MenuGroupLabel>Terms sections</MenuGroupLabel>
                {terms.sections.map((section) => {
                  const draft = drafts[section.slug] ?? sectionDraft(section);
                  const paragraphs = splitParagraphs(draft.body_en).length;
                  const formLines = splitLines(draft.model_form_lines_en)?.length ?? 0;
                  return (
                    <TargetCard
                      key={section.slug}
                      title={section.title_en}
                      detail={section.slug}
                      selected={selectedTarget === section.slug}
                      countLabel={`${paragraphs} paragraph${paragraphs === 1 ? "" : "s"}${formLines > 0 ? ` · ${formLines} form line${formLines === 1 ? "" : "s"}` : ""}`}
                      gaps={termsSectionTranslationGaps(section, draft, () => setSelectedTarget(section.slug))}
                      onSelect={() => setSelectedTarget(section.slug)}
                    />
                  );
                })}
              </div>
            </div>
          </aside>

          <section className="min-w-0 overflow-hidden rounded-brand border border-admin-border/50 bg-admin-surface shadow-sm">
            {selectedTarget === "page" ? (
              <PageEditor page={terms.page} onChange={updatePageField} onSave={savePage} />
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

function PageEditor({ page, onChange, onSave }: { page: TermsPageAdminResponse; onChange: (field: PageField, value: string) => void; onSave: () => void }) {
  const t = useTranslations("admin.terms");
  return (
    <div>
      <EditorHeader title={t("pageSection")} detail="SEO, hero, related policy links, and page navigation labels." />
      <div className="space-y-5 p-4 sm:p-5">
        <div className="grid min-w-0 gap-5 lg:grid-cols-2">
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
  section: TermsSectionAdminResponse;
  draft: SectionDraft;
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
  onSave: () => void;
}) {
  const t = useTranslations("admin.terms");
  return (
    <div>
      <EditorHeader title={section.title_en} detail={`${section.slug} · ${section.body_en.length} paragraph${section.body_en.length === 1 ? "" : "s"}`} />
      <div className="space-y-5 p-4 sm:p-5">
        <div className="grid min-w-0 gap-5 lg:grid-cols-2">
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
      <h2 className="break-words font-heading text-2xl font-semibold text-charcoal">{title}</h2>
      <p className="mt-1 text-sm leading-6 text-soft-brown">{detail}</p>
    </div>
  );
}

function TargetCard({ title, detail, selected, countLabel, gaps, onSelect }: {
  title: string;
  detail: string;
  selected: boolean;
  countLabel: string;
  gaps: AdminTranslationGap[];
  onSelect: () => void;
}) {
  return (
    <article className={cn("rounded-brand border bg-admin-surface p-3 transition-colors", selected ? "border-admin-primary shadow-md" : "border-admin-border/45 hover:border-admin-accent")}>
      <button type="button" onClick={onSelect} className="block w-full min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface" aria-current={selected ? "true" : undefined}>
        <h3 className="truncate font-heading text-lg text-charcoal">{title}</h3>
        <p className="mt-0.5 truncate text-xs text-soft-brown">{detail}</p>
      </button>
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-pill border border-champagne-beige bg-warm-ivory px-2 py-1 text-xs font-semibold text-soft-brown">{countLabel}</span>
        <AdminTranslationGapButton gaps={gaps} label={`${title} translation gaps`} />
      </div>
    </article>
  );
}

function MenuGroupLabel({ children }: { children: string }) {
  return (
    <p className="px-1 text-[11px] font-semibold uppercase tracking-wide text-muted-gold">
      {children}
    </p>
  );
}

function OverviewTile({ label, value, detail, warning = false }: { label: string; value: ReactNode; detail: string; warning?: boolean }) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-soft-brown">{label}</p>
      <div className="mt-1 flex items-end gap-2">
        <div className={cn("font-heading text-2xl font-semibold", warning ? "text-amber-700" : "text-charcoal")}>{value}</div>
        <span className="pb-1 text-xs text-soft-brown">{detail}</span>
      </div>
    </div>
  );
}

function StickyActions({ children }: { children: ReactNode }) {
  return <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-brand border border-admin-border/50 bg-admin-surface/95 p-3 shadow-lg backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">{children}</div>;
}

function LanguagePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-w-0 space-y-4 rounded-brand border border-champagne-beige bg-warm-ivory p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-gold">{title}</h3>
      {children}
    </div>
  );
}

function PageFields({ page, suffix, onChange }: { page: TermsPageAdminResponse; suffix: "en" | "bg"; onChange: (field: PageField, value: string) => void }) {
  const t = useTranslations("admin.terms");
  const field = (name: string) => `${name}_${suffix}` as PageField;
  const gapProps = (name: string, label: string, en: string | null | undefined, bg: string | null | undefined) => suffix === "bg"
    ? { id: termsPageFieldId(name), label: <>{label}<MissingBgLabel show={isMissingTranslation(en, bg)} /></> }
    : { label };
  return (
    <div className="space-y-3">
      <TextInput {...gapProps("meta-title", t("metaTitle"), page.meta_title_en, page.meta_title_bg)} value={String(page[field("meta_title")] ?? "")} onChange={(value) => onChange(field("meta_title"), value)} />
      <TextArea {...gapProps("meta-description", t("metaDescription"), page.meta_description_en, page.meta_description_bg)} rows={3} value={String(page[field("meta_description")] ?? "")} onChange={(value) => onChange(field("meta_description"), value)} />
      <TextInput {...gapProps("eyebrow", t("eyebrow"), page.eyebrow_en, page.eyebrow_bg)} value={String(page[field("eyebrow")] ?? "")} onChange={(value) => onChange(field("eyebrow"), value)} />
      <TextInput {...gapProps("title", t("pageTitle"), page.title_en, page.title_bg)} value={String(page[field("title")] ?? "")} onChange={(value) => onChange(field("title"), value)} />
      <TextArea {...gapProps("subtitle", t("subtitleField"), page.subtitle_en, page.subtitle_bg)} rows={3} value={String(page[field("subtitle")] ?? "")} onChange={(value) => onChange(field("subtitle"), value)} />
      <TextInput {...gapProps("last-updated", t("lastUpdated"), page.last_updated_en, page.last_updated_bg)} value={String(page[field("last_updated")] ?? "")} onChange={(value) => onChange(field("last_updated"), value)} />
      <TextArea {...gapProps("identity-intro", t("identityIntro"), page.identity_intro_en, page.identity_intro_bg)} rows={3} value={String(page[field("identity_intro")] ?? "")} onChange={(value) => onChange(field("identity_intro"), value)} />
      <TextInput {...gapProps("policy-links-title", t("policyLinksTitle"), page.policy_links_title_en, page.policy_links_title_bg)} value={String(page[field("policy_links_title")] ?? "")} onChange={(value) => onChange(field("policy_links_title"), value)} />
      <TextInput {...gapProps("privacy-link", t("privacyLink"), page.privacy_link_en, page.privacy_link_bg)} value={String(page[field("privacy_link")] ?? "")} onChange={(value) => onChange(field("privacy_link"), value)} />
      <TextInput {...gapProps("cookies-link", t("cookiesLink"), page.cookies_link_en, page.cookies_link_bg)} value={String(page[field("cookies_link")] ?? "")} onChange={(value) => onChange(field("cookies_link"), value)} />
      <TextInput {...gapProps("nav-label", t("navLabel"), page.nav_label_en, page.nav_label_bg)} value={String(page[field("nav_label")] ?? "")} onChange={(value) => onChange(field("nav_label"), value)} />
      <TextInput {...gapProps("back-to-top", t("backToTop"), page.back_to_top_en, page.back_to_top_bg)} value={String(page[field("back_to_top")] ?? "")} onChange={(value) => onChange(field("back_to_top"), value)} />
    </div>
  );
}

function SectionFields({ section, draft, suffix, onSectionChange, onDraftChange }: {
  section: TermsSectionAdminResponse;
  draft: SectionDraft;
  suffix: "en" | "bg";
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
}) {
  const t = useTranslations("admin.terms");
  const titleField = `title_${suffix}` as SectionTextField;
  const navField = `nav_${suffix}` as SectionTextField;
  const modelTitleField = `model_form_title_${suffix}` as SectionTextField;
  const modelIntroField = `model_form_intro_${suffix}` as SectionTextField;
  const bodyField = `body_${suffix}` as keyof SectionDraft;
  const modelLinesField = `model_form_lines_${suffix}` as keyof SectionDraft;
  const gapProps = (name: string, label: string, en: string | null | undefined, bg: string | null | undefined) => suffix === "bg"
    ? { id: termsSectionFieldId(section.slug, name), label: <>{label}<MissingBgLabel show={isMissingTranslation(en, bg)} /></> }
    : { label };

  return (
    <div className="space-y-3">
      <TextInput {...gapProps("title", t("sectionTitle"), section.title_en, section.title_bg)} value={String(section[titleField] ?? "")} onChange={(value) => onSectionChange(titleField, value)} />
      <TextInput {...gapProps("nav", t("sectionNav"), section.nav_en, section.nav_bg)} value={String(section[navField] ?? "")} onChange={(value) => onSectionChange(navField, value)} />
      <TextArea {...gapProps("body", t("body"), draft.body_en, draft.body_bg)} rows={8} value={draft[bodyField]} onChange={(value) => onDraftChange(bodyField, value)} />
      <TextInput {...gapProps("model-form-title", t("modelFormTitle"), section.model_form_title_en, section.model_form_title_bg)} value={String(section[modelTitleField] ?? "")} onChange={(value) => onSectionChange(modelTitleField, value)} />
      <TextArea {...gapProps("model-form-intro", t("modelFormIntro"), section.model_form_intro_en, section.model_form_intro_bg)} rows={3} value={String(section[modelIntroField] ?? "")} onChange={(value) => onSectionChange(modelIntroField, value)} />
      <TextArea {...gapProps("model-form-lines", t("modelFormLines"), draft.model_form_lines_en, draft.model_form_lines_bg)} rows={5} value={draft[modelLinesField]} onChange={(value) => onDraftChange(modelLinesField, value)} />
    </div>
  );
}

function TextInput({ id, label, value, onChange }: { id?: string; label: ReactNode; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input id={id} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" />
    </label>
  );
}

function TextArea({ id, label, rows, value, onChange }: { id?: string; label: ReactNode; rows: number; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea id={id} value={value} rows={rows} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" />
    </label>
  );
}

function summarizeTerms(terms: TermsAdminResponse | null, drafts: Record<string, SectionDraft>) {
  const sections = terms?.sections ?? [];
  return {
    sections: sections.length,
    paragraphs: sections.reduce((total, section) => total + (drafts[section.slug]?.body_en ? splitParagraphs(drafts[section.slug]!.body_en).length : section.body_en.length), 0),
    formLines: sections.reduce((total, section) => total + (drafts[section.slug]?.model_form_lines_en ? splitLines(drafts[section.slug]!.model_form_lines_en)?.length ?? 0 : section.model_form_lines_en?.length ?? 0), 0),
    translationGaps: (terms ? pageTranslationGapCount(terms.page) : 0) + sections.reduce((total, section) => total + sectionTranslationGapCount(section, drafts[section.slug] ?? sectionDraft(section)), 0),
  };
}

function pageTranslationGapCount(page: TermsPageAdminResponse) {
  return termsPageTranslationGaps(page).length;
}

function sectionTranslationGapCount(section: TermsSectionAdminResponse, draft: SectionDraft) {
  return termsSectionTranslationGaps(section, draft).length;
}

function termsPageTranslationGaps(page: TermsPageAdminResponse, onFix?: () => void): AdminTranslationGap[] {
  const fields: Array<[string, string, string | null | undefined, string | null | undefined]> = [
    ["meta-title", "Page > Meta title BG", page.meta_title_en, page.meta_title_bg],
    ["meta-description", "Page > Meta description BG", page.meta_description_en, page.meta_description_bg],
    ["eyebrow", "Page > Eyebrow BG", page.eyebrow_en, page.eyebrow_bg],
    ["title", "Page > Title BG", page.title_en, page.title_bg],
    ["subtitle", "Page > Subtitle BG", page.subtitle_en, page.subtitle_bg],
    ["last-updated", "Page > Last updated BG", page.last_updated_en, page.last_updated_bg],
    ["identity-intro", "Page > Identity intro BG", page.identity_intro_en, page.identity_intro_bg],
    ["policy-links-title", "Page > Policy links title BG", page.policy_links_title_en, page.policy_links_title_bg],
    ["privacy-link", "Page > Privacy link BG", page.privacy_link_en, page.privacy_link_bg],
    ["cookies-link", "Page > Cookies link BG", page.cookies_link_en, page.cookies_link_bg],
    ["nav-label", "Page > Nav label BG", page.nav_label_en, page.nav_label_bg],
    ["back-to-top", "Page > Back to top BG", page.back_to_top_en, page.back_to_top_bg],
  ];
  return fields
    .filter(([, , en, bg]) => isMissingTranslation(en, bg))
    .map(([name, label]) => ({ id: `terms-page-${name}`, label, fieldId: termsPageFieldId(name), onFix }));
}

function termsSectionTranslationGaps(section: TermsSectionAdminResponse, draft: SectionDraft, onFix?: () => void): AdminTranslationGap[] {
  const title = section.title_en || section.slug;
  const fields: Array<[string, string, string | null | undefined, string | null | undefined]> = [
    ["title", `${title} > Title BG`, section.title_en, section.title_bg],
    ["nav", `${title} > Nav BG`, section.nav_en, section.nav_bg],
    ["body", `${title} > Body BG`, draft.body_en, draft.body_bg],
    ["model-form-title", `${title} > Model form title BG`, section.model_form_title_en, section.model_form_title_bg],
    ["model-form-intro", `${title} > Model form intro BG`, section.model_form_intro_en, section.model_form_intro_bg],
    ["model-form-lines", `${title} > Model form lines BG`, draft.model_form_lines_en, draft.model_form_lines_bg],
  ];
  return fields
    .filter(([, , en, bg]) => isMissingTranslation(en, bg))
    .map(([name, label]) => ({ id: `terms-${section.slug}-${name}`, label, fieldId: termsSectionFieldId(section.slug, name), onFix }));
}

function termsPageFieldId(name: string) {
  return `terms-page-${name}-bg`;
}

function termsSectionFieldId(slug: string, name: string) {
  return `terms-${slug}-${name}-bg`;
}
