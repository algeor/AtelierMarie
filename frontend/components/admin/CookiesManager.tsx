"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import {
  getAdminCookies,
  updateCookieSection,
  updateCookiesPage,
} from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import type {
  CookieInventoryAdminResponse,
  CookieSectionAdminResponse,
  CookiesAdminResponse,
  CookiesPageAdminResponse,
} from "@/lib/types";

type PageField = keyof Omit<CookiesPageAdminResponse, "id" | "created_at" | "updated_at">;
type SectionTextField = "title_en" | "title_bg";
type SectionDraft = { body_en: string; body_bg: string };

function joinParagraphs(lines: string[] | null): string {
  return lines?.join("\n\n") ?? "";
}

function splitParagraphs(value: string): string[] {
  return value
    .split(/\n\s*\n/g)
    .map((line) => line.trim())
    .filter(Boolean);
}

function sectionDraft(section: CookieSectionAdminResponse): SectionDraft {
  return { body_en: joinParagraphs(section.body_en), body_bg: joinParagraphs(section.body_bg) };
}

const EMPTY_DRAFT: SectionDraft = { body_en: "", body_bg: "" };

export function CookiesManager() {
  const t = useTranslations("admin.cookies");
  const tCommon = useTranslations("common");
  const [policy, setPolicy] = useState<CookiesAdminResponse | null>(null);
  const [drafts, setDrafts] = useState<Record<string, SectionDraft>>({});
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAdminCookies()
      .then((data) => {
        if (cancelled) return;
        setPolicy(data);
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
    setPolicy((current) =>
      current ? { ...current, page: { ...current.page, [field]: value } } : current
    );
  }

  function updateSectionField(slug: string, field: SectionTextField, value: string) {
    setPolicy((current) =>
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
    if (!policy) return;
    setError(null);
    try {
      const page = await updateCookiesPage({
        meta_title_en: policy.page.meta_title_en,
        meta_title_bg: policy.page.meta_title_bg || null,
        meta_description_en: policy.page.meta_description_en,
        meta_description_bg: policy.page.meta_description_bg || null,
        eyebrow_en: policy.page.eyebrow_en,
        eyebrow_bg: policy.page.eyebrow_bg || null,
        title_en: policy.page.title_en,
        title_bg: policy.page.title_bg || null,
        subtitle_en: policy.page.subtitle_en,
        subtitle_bg: policy.page.subtitle_bg || null,
        last_updated_en: policy.page.last_updated_en,
        last_updated_bg: policy.page.last_updated_bg || null,
        inventory_title_en: policy.page.inventory_title_en,
        inventory_title_bg: policy.page.inventory_title_bg || null,
        header_name_en: policy.page.header_name_en,
        header_name_bg: policy.page.header_name_bg || null,
        header_purpose_en: policy.page.header_purpose_en,
        header_purpose_bg: policy.page.header_purpose_bg || null,
        header_type_en: policy.page.header_type_en,
        header_type_bg: policy.page.header_type_bg || null,
        header_duration_en: policy.page.header_duration_en,
        header_duration_bg: policy.page.header_duration_bg || null,
      });
      setPolicy((current) => (current ? { ...current, page } : current));
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function saveSection(section: CookieSectionAdminResponse) {
    const draft = drafts[section.slug] ?? sectionDraft(section);
    setError(null);
    try {
      const updated = await updateCookieSection(section.slug, {
        title_en: section.title_en,
        title_bg: section.title_bg || null,
        body_en: splitParagraphs(draft.body_en),
        body_bg: splitParagraphs(draft.body_bg),
      });
      setPolicy((current) =>
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

  if (!policy && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="space-y-6">
      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {policy && (
        <section className="rounded-brand border border-champagne-beige bg-cream p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-heading text-xl text-charcoal">{t("pageSection")}</h2>
            <button type="button" onClick={savePage} className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white">
              {t("savePage")}
            </button>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <LanguagePanel title={t("english")}>
              <PageFields page={policy.page} suffix="en" onChange={updatePageField} />
            </LanguagePanel>
            <LanguagePanel title={t("bulgarian")}>
              <PageFields page={policy.page} suffix="bg" onChange={updatePageField} />
            </LanguagePanel>
          </div>
        </section>
      )}

      {policy && (
        <section className="rounded-brand border border-champagne-beige bg-cream p-5">
          <div>
            <h2 className="font-heading text-xl text-charcoal">{t("inventorySection")}</h2>
            <p className="mt-1 text-sm leading-6 text-soft-brown">{t("inventoryAutoNote")}</p>
          </div>
          <div className="mt-5 space-y-4">
            {policy.cookies.map((item) => (
              <div key={item.name} className="rounded-brand border border-champagne-beige bg-white p-4">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="font-mono text-sm font-semibold text-charcoal">{item.name}</h3>
                    <p className="mt-1 text-xs text-soft-brown">
                      {t("source")}: {item.source} · {t("lastSeen")}: {item.last_seen_at || t("unknown")}
                    </p>
                  </div>
                  <span className="rounded-full bg-muted-gold/15 px-3 py-1 text-xs font-semibold text-charcoal">
                    {item.auto_detected ? t("autoDetected") : t("manualRow")}
                  </span>
                </div>
                <div className="grid gap-5 lg:grid-cols-2">
                  <LanguagePanel title={t("english")}>
                    <InventoryFields item={item} suffix="en" />
                  </LanguagePanel>
                  <LanguagePanel title={t("bulgarian")}>
                    <InventoryFields item={item} suffix="bg" />
                  </LanguagePanel>
                </div>
                {item.observed_on.length > 0 && (
                  <p className="mt-3 break-words text-xs leading-5 text-soft-brown">
                    {t("observedOn")}: {item.observed_on.join(", ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {policy?.sections.map((section) => {
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
  page: CookiesPageAdminResponse;
  suffix: "en" | "bg";
  onChange: (field: PageField, value: string) => void;
}) {
  const t = useTranslations("admin.cookies");
  const field = (name: string) => `${name}_${suffix}` as PageField;
  return (
    <div className="space-y-3">
      <TextInput label={t("metaTitle")} value={String(page[field("meta_title")] ?? "")} onChange={(value) => onChange(field("meta_title"), value)} />
      <TextArea label={t("metaDescription")} rows={3} value={String(page[field("meta_description")] ?? "")} onChange={(value) => onChange(field("meta_description"), value)} />
      <TextInput label={t("eyebrow")} value={String(page[field("eyebrow")] ?? "")} onChange={(value) => onChange(field("eyebrow"), value)} />
      <TextInput label={t("pageTitle")} value={String(page[field("title")] ?? "")} onChange={(value) => onChange(field("title"), value)} />
      <TextArea label={t("subtitleField")} rows={3} value={String(page[field("subtitle")] ?? "")} onChange={(value) => onChange(field("subtitle"), value)} />
      <TextInput label={t("lastUpdated")} value={String(page[field("last_updated")] ?? "")} onChange={(value) => onChange(field("last_updated"), value)} />
      <TextInput label={t("inventoryTitle")} value={String(page[field("inventory_title")] ?? "")} onChange={(value) => onChange(field("inventory_title"), value)} />
      <TextInput label={t("headerName")} value={String(page[field("header_name")] ?? "")} onChange={(value) => onChange(field("header_name"), value)} />
      <TextInput label={t("headerPurpose")} value={String(page[field("header_purpose")] ?? "")} onChange={(value) => onChange(field("header_purpose"), value)} />
      <TextInput label={t("headerType")} value={String(page[field("header_type")] ?? "")} onChange={(value) => onChange(field("header_type"), value)} />
      <TextInput label={t("headerDuration")} value={String(page[field("header_duration")] ?? "")} onChange={(value) => onChange(field("header_duration"), value)} />
    </div>
  );
}

function InventoryFields({
  item,
  suffix,
}: {
  item: CookieInventoryAdminResponse;
  suffix: "en" | "bg";
}) {
  const t = useTranslations("admin.cookies");
  const purpose = suffix === "bg" ? item.purpose_bg || item.purpose_en : item.purpose_en;
  const type = suffix === "bg" ? item.type_bg || item.type_en : item.type_en;
  const duration = suffix === "bg" ? item.duration_bg || item.duration_en : item.duration_en;
  return (
    <div className="space-y-3 text-sm">
      <ReadOnlyField label={t("purpose")} value={purpose} />
      <ReadOnlyField label={t("type")} value={type} />
      <ReadOnlyField label={t("duration")} value={duration} />
    </div>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-gold">{label}</p>
      <p className="mt-1 break-words leading-6 text-charcoal">{value}</p>
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
  section: CookieSectionAdminResponse;
  draft: SectionDraft;
  suffix: "en" | "bg";
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
}) {
  const t = useTranslations("admin.cookies");
  const titleField = `title_${suffix}` as SectionTextField;
  const bodyField = `body_${suffix}` as keyof SectionDraft;
  return (
    <div className="space-y-3">
      <TextInput label={t("sectionTitle")} value={String(section[titleField] ?? "")} onChange={(value) => onSectionChange(titleField, value)} />
      <TextArea label={t("body")} rows={8} value={draft[bodyField]} onChange={(value) => onDraftChange(bodyField, value)} />
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
