"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { getAdminPrivacy, updatePrivacyPage, updatePrivacySection } from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import type {
  PrivacyAdminResponse,
  PrivacyPageAdminResponse,
  PrivacySectionAdminResponse,
} from "@/lib/types";

type PageField = keyof Omit<PrivacyPageAdminResponse, "id" | "created_at" | "updated_at">;
type SectionTextField = "title_en" | "title_bg" | "nav_en" | "nav_bg";
type SectionDraft = { body_en: string; body_bg: string };

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
    setPrivacy((current) =>
      current ? { ...current, page: { ...current.page, [field]: value } } : current
    );
  }

  function updateSectionField(slug: string, field: SectionTextField, value: string) {
    setPrivacy((current) =>
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

  if (!privacy && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="space-y-6">
      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {privacy && (
        <section className="rounded-brand border border-champagne-beige bg-cream p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-heading text-xl text-charcoal">{t("pageSection")}</h2>
            <button type="button" onClick={savePage} className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white">
              {t("savePage")}
            </button>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <LanguagePanel title={t("english")}>
              <PageFields page={privacy.page} suffix="en" onChange={updatePageField} />
            </LanguagePanel>
            <LanguagePanel title={t("bulgarian")}>
              <PageFields page={privacy.page} suffix="bg" onChange={updatePageField} />
            </LanguagePanel>
          </div>
        </section>
      )}

      {privacy?.sections.map((section) => {
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
  page: PrivacyPageAdminResponse;
  suffix: "en" | "bg";
  onChange: (field: PageField, value: string) => void;
}) {
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

function SectionFields({
  section,
  draft,
  suffix,
  onSectionChange,
  onDraftChange,
}: {
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
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm text-charcoal"
      />
    </label>
  );
}

function TextArea({ label, value, rows, onChange }: { label: string; value: string; rows: number; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea
        value={value}
        rows={rows}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm leading-6 text-charcoal"
      />
    </label>
  );
}
