"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { getAdminTerms, updateTermsPage, updateTermsSection } from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
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
  const [terms, setTerms] = useState<TermsAdminResponse | null>(null);
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
        setDrafts(
          Object.fromEntries(data.sections.map((section) => [section.slug, sectionDraft(section)]))
        );
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

  function showSaved(message = tCommon("saved")) {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function updatePageField(field: PageField, value: string) {
    setTerms((current) =>
      current ? { ...current, page: { ...current.page, [field]: value } } : current
    );
  }

  function updateSectionField(slug: string, field: SectionTextField, value: string) {
    setTerms((current) =>
      current
        ? {
            ...current,
            sections: current.sections.map((section) =>
              section.slug === slug ? { ...section, [field]: value } : section
            ),
          }
        : current
    );
  }

  function updateDraft(slug: string, field: keyof SectionDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [slug]: { ...(current[slug] ?? { body_en: "", body_bg: "", model_form_lines_en: "", model_form_lines_bg: "" }), [field]: value },
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
              sections: current.sections.map((candidate) =>
                candidate.slug === updated.slug ? updated : candidate
              ),
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
    <div className="space-y-6">
      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {terms && (
        <section className="rounded-brand border border-champagne-beige bg-cream p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-heading text-xl text-charcoal">{t("pageSection")}</h2>
            <button type="button" onClick={savePage} className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white">
              {t("savePage")}
            </button>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <LanguagePanel title={t("english")}>
              <PageFields page={terms.page} suffix="en" onChange={updatePageField} />
            </LanguagePanel>
            <LanguagePanel title={t("bulgarian")}>
              <PageFields page={terms.page} suffix="bg" onChange={updatePageField} />
            </LanguagePanel>
          </div>
        </section>
      )}

      {terms?.sections.map((section) => {
        const draft = drafts[section.slug] ?? sectionDraft(section);
        return (
          <section key={section.slug} className="rounded-brand border border-champagne-beige bg-cream p-5">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-gold">{section.slug}</p>
                <h2 className="font-heading text-xl text-charcoal">{section.title_bg || section.title_en}</h2>
              </div>
              <button type="button" onClick={() => saveSection(section)} className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white">
                {t("saveSection")}
              </button>
            </div>
            <div className="grid gap-5 lg:grid-cols-2">
              <LanguagePanel title={t("english")}>
                <SectionFields
                  section={section}
                  draft={draft}
                  suffix="en"
                  onSectionChange={(field, value) => updateSectionField(section.slug, field, value)}
                  onDraftChange={(field, value) => updateDraft(section.slug, field, value)}
                />
              </LanguagePanel>
              <LanguagePanel title={t("bulgarian")}>
                <SectionFields
                  section={section}
                  draft={draft}
                  suffix="bg"
                  onSectionChange={(field, value) => updateSectionField(section.slug, field, value)}
                  onDraftChange={(field, value) => updateDraft(section.slug, field, value)}
                />
              </LanguagePanel>
            </div>
          </section>
        );
      })}
    </div>
  );
}

function LanguagePanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-4 rounded-brand border border-champagne-beige bg-white p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-gold">{title}</h3>
      {children}
    </div>
  );
}

function PageFields({
  page,
  suffix,
  onChange,
}: {
  page: TermsPageAdminResponse;
  suffix: "en" | "bg";
  onChange: (field: PageField, value: string) => void;
}) {
  const t = useTranslations("admin.terms");
  const field = (name: string) => `${name}_${suffix}` as PageField;
  return (
    <div className="space-y-3">
      <TextInput label={t("metaTitle")} value={String(page[field("meta_title")] ?? "")} onChange={(value) => onChange(field("meta_title"), value)} />
      <TextArea label={t("metaDescription")} rows={3} value={String(page[field("meta_description")] ?? "")} onChange={(value) => onChange(field("meta_description"), value)} />
      <TextInput label={t("eyebrow")} value={String(page[field("eyebrow")] ?? "")} onChange={(value) => onChange(field("eyebrow"), value)} />
      <TextInput label={t("pageTitle")} value={String(page[field("title")] ?? "")} onChange={(value) => onChange(field("title"), value)} />
      <TextArea label={t("subtitleField")} rows={3} value={String(page[field("subtitle")] ?? "")} onChange={(value) => onChange(field("subtitle"), value)} />
      <TextInput label={t("lastUpdated")} value={String(page[field("last_updated")] ?? "")} onChange={(value) => onChange(field("last_updated"), value)} />
      <TextArea label={t("identityIntro")} rows={3} value={String(page[field("identity_intro")] ?? "")} onChange={(value) => onChange(field("identity_intro"), value)} />
      <TextInput label={t("policyLinksTitle")} value={String(page[field("policy_links_title")] ?? "")} onChange={(value) => onChange(field("policy_links_title"), value)} />
      <TextInput label={t("privacyLink")} value={String(page[field("privacy_link")] ?? "")} onChange={(value) => onChange(field("privacy_link"), value)} />
      <TextInput label={t("cookiesLink")} value={String(page[field("cookies_link")] ?? "")} onChange={(value) => onChange(field("cookies_link"), value)} />
      <TextInput label={t("navLabel")} value={String(page[field("nav_label")] ?? "")} onChange={(value) => onChange(field("nav_label"), value)} />
      <TextInput label={t("backToTop")} value={String(page[field("back_to_top")] ?? "")} onChange={(value) => onChange(field("back_to_top"), value)} />
    </div>
  );
}

function SectionFields({
  section,
  draft,
  suffix,
  onSectionChange,
  onDraftChange,
}: {
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

  return (
    <div className="space-y-3">
      <TextInput label={t("sectionTitle")} value={String(section[titleField] ?? "")} onChange={(value) => onSectionChange(titleField, value)} />
      <TextInput label={t("sectionNav")} value={String(section[navField] ?? "")} onChange={(value) => onSectionChange(navField, value)} />
      <TextArea label={t("body")} rows={8} value={draft[bodyField]} onChange={(value) => onDraftChange(bodyField, value)} />
      <TextInput label={t("modelFormTitle")} value={String(section[modelTitleField] ?? "")} onChange={(value) => onSectionChange(modelTitleField, value)} />
      <TextArea label={t("modelFormIntro")} rows={3} value={String(section[modelIntroField] ?? "")} onChange={(value) => onSectionChange(modelIntroField, value)} />
      <TextArea label={t("modelFormLines")} rows={5} value={draft[modelLinesField]} onChange={(value) => onDraftChange(modelLinesField, value)} />
    </div>
  );
}

function TextInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige px-3 py-2 text-sm text-charcoal" />
    </label>
  );
}

function TextArea({ label, rows, value, onChange }: { label: string; rows: number; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea value={value} rows={rows} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige px-3 py-2 text-sm text-charcoal" />
    </label>
  );
}
