"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { AdminMobileTargetSelect } from "@/components/admin/AdminMobileTargetSelect";
import { AdminTranslationGapButton, MissingBgLabel, isMissingTranslation, type AdminTranslationGap } from "@/components/admin/AdminTranslationGaps";
import {
  getAdminCookies,
  updateCookieSection,
  updateCookiesPage,
} from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type {
  CookieInventoryAdminResponse,
  CookieSectionAdminResponse,
  CookiesAdminResponse,
  CookiesPageAdminResponse,
} from "@/lib/types";

type PageField = keyof Omit<CookiesPageAdminResponse, "id" | "created_at" | "updated_at">;
type SectionTextField = "title_en" | "title_bg";
type SectionDraft = { body_en: string; body_bg: string };
type Target = "page" | "inventory" | `section:${string}`;

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

function sectionDraft(section: CookieSectionAdminResponse): SectionDraft {
  return { body_en: joinParagraphs(section.body_en), body_bg: joinParagraphs(section.body_bg) };
}

export function CookiesManager() {
  const t = useTranslations("admin.cookies");
  const tCommon = useTranslations("common");
  const searchParams = useSearchParams();
  const [policy, setPolicy] = useState<CookiesAdminResponse | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<Target>("page");
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
    if (!policy) return;
    const requestedTarget = searchParams?.get("target") ?? null;
    const requestedSectionSlug = requestedTarget?.startsWith("section:") ? requestedTarget.replace("section:", "") : null;
    if (
      requestedTarget === "page" ||
      requestedTarget === "inventory" ||
      (requestedSectionSlug && policy.sections.some((section) => section.slug === requestedSectionSlug))
    ) {
      setSelectedTarget(requestedTarget as Target);
      return;
    }

    if (selectedTarget === "page" || selectedTarget === "inventory") return;
    const slug = selectedTarget.replace("section:", "");
    if (!policy.sections.some((section) => section.slug === slug)) setSelectedTarget("page");
  }, [policy, selectedTarget, searchParams]);

  const selectedSection =
    selectedTarget.startsWith("section:")
      ? policy?.sections.find((section) => `section:${section.slug}` === selectedTarget) ?? null
      : null;
  const overview = useMemo(() => summarizeCookies(policy, drafts), [policy, drafts]);
  const allTranslationGaps = policy ? [
    ...cookiesPageTranslationGaps(policy.page, () => setSelectedTarget("page")),
    ...policy.cookies.flatMap((item) => cookieInventoryTranslationGaps(item, () => setSelectedTarget("inventory"))),
    ...policy.sections.flatMap((section) => cookieSectionTranslationGaps(section, drafts[section.slug] ?? sectionDraft(section), () => setSelectedTarget(`section:${section.slug}`))),
  ] : [];
  const mobileTargetOptions = policy ? [
    {
      value: "page",
      label: t("pageSection"),
      group: "Page",
      description: "SEO, hero, inventory labels, and table headers",
    },
    {
      value: "inventory",
      label: t("inventorySection"),
      group: "Inventory",
      description: `${policy.cookies.length} row${policy.cookies.length === 1 ? "" : "s"} · ${policy.cookies.filter((item) => item.is_active).length} active`,
    },
    ...policy.sections.map((section) => {
      const draft = drafts[section.slug] ?? sectionDraft(section);
      const paragraphs = splitParagraphs(draft.body_en).length;
      return {
        value: `section:${section.slug}`,
        label: section.title_en,
        group: "Policy sections",
        description: `${paragraphs} paragraph${paragraphs === 1 ? "" : "s"}`,
      };
    }),
  ] : [];

  function showSaved(message = tCommon("saved")) {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function updatePageField(field: PageField, value: string) {
    setPolicy((current) => current ? { ...current, page: { ...current.page, [field]: value } } : current);
  }

  function updateSectionField(slug: string, field: SectionTextField, value: string) {
    setPolicy((current) =>
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

  if (!policy && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="min-w-0 space-y-5">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">Legal copy workspace</p>
          <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
          <p className="mt-1 text-sm leading-6 text-soft-brown">{t("subtitle")}</p>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewTile label="Inventory" value={String(overview.cookies)} detail="cookie rows" />
          <OverviewTile label="Active" value={String(overview.activeCookies)} detail="currently listed" />
          <OverviewTile label="Sections" value={String(overview.sections)} detail="policy blocks" />
          <OverviewTile label="Translation gaps" value={<AdminTranslationGapButton gaps={allTranslationGaps} label="Cookies translation gaps" />} detail="need review" warning={overview.translationGaps > 0} />
        </div>
      </header>

      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {policy ? (
        <div className="grid min-w-0 gap-5 xl:grid-cols-[21rem_minmax(0,1fr)]">
          <AdminMobileTargetSelect
            label="Edit target"
            value={selectedTarget}
            onChange={(value) => setSelectedTarget(value as Target)}
            options={mobileTargetOptions}
          />

          <aside className="hidden min-w-0 space-y-3 xl:sticky xl:top-24 xl:block xl:self-start">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-heading text-xl font-semibold text-charcoal">Edit target</h2>
              <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{policy.sections.length + 2} total</span>
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <MenuGroupLabel>Page</MenuGroupLabel>
                <TargetCard
                  title={t("pageSection")}
                  detail={policy.page.title_en}
                  selected={selectedTarget === "page"}
                  countLabel="SEO, hero, table headers"
                  gaps={cookiesPageTranslationGaps(policy.page, () => setSelectedTarget("page"))}
                  onSelect={() => setSelectedTarget("page")}
                />
              </div>

              <div className="space-y-2">
                <MenuGroupLabel>Inventory</MenuGroupLabel>
                <TargetCard
                  title={t("inventorySection")}
                  detail={t("inventoryAutoNote")}
                  selected={selectedTarget === "inventory"}
                  countLabel={`${policy.cookies.length} row${policy.cookies.length === 1 ? "" : "s"}`}
                  gaps={policy.cookies.flatMap((item) => cookieInventoryTranslationGaps(item, () => setSelectedTarget("inventory")))}
                  onSelect={() => setSelectedTarget("inventory")}
                />
              </div>

              <div className="space-y-2">
                <MenuGroupLabel>Policy sections</MenuGroupLabel>
                {policy.sections.map((section) => {
                  const draft = drafts[section.slug] ?? sectionDraft(section);
                  const paragraphs = splitParagraphs(draft.body_en).length;
                  return (
                    <TargetCard
                      key={section.slug}
                      title={section.title_en}
                      detail={section.slug}
                      selected={selectedTarget === `section:${section.slug}`}
                      countLabel={`${paragraphs} paragraph${paragraphs === 1 ? "" : "s"}`}
                      gaps={cookieSectionTranslationGaps(section, draft, () => setSelectedTarget(`section:${section.slug}`))}
                      onSelect={() => setSelectedTarget(`section:${section.slug}`)}
                    />
                  );
                })}
              </div>
            </div>
          </aside>

          <section className="min-w-0 overflow-hidden rounded-brand border border-admin-border/50 bg-admin-surface shadow-sm">
            {selectedTarget === "page" ? (
              <PageEditor page={policy.page} onChange={updatePageField} onSave={savePage} />
            ) : selectedTarget === "inventory" ? (
              <InventoryEditor cookies={policy.cookies} />
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

function PageEditor({ page, onChange, onSave }: { page: CookiesPageAdminResponse; onChange: (field: PageField, value: string) => void; onSave: () => void }) {
  const t = useTranslations("admin.cookies");
  return (
    <div>
      <EditorHeader title={t("pageSection")} detail="SEO, hero, date, inventory labels, and table headers for the public cookie page." />
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

function InventoryEditor({ cookies }: { cookies: CookieInventoryAdminResponse[] }) {
  const t = useTranslations("admin.cookies");
  return (
    <div>
      <EditorHeader title={t("inventorySection")} detail={t("inventoryAutoNote")} />
      <div className="space-y-4 p-4 sm:p-5">
        {cookies.map((item) => (
          <article key={item.name} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <h3 className="break-words font-mono text-sm font-semibold text-charcoal">{item.name}</h3>
                <p className="mt-1 text-xs text-soft-brown">
                  {t("source")}: {item.source} · {t("lastSeen")}: {item.last_seen_at || t("unknown")}
                </p>
              </div>
              <span className="rounded-pill border border-champagne-beige bg-admin-surface px-2 py-1 text-xs font-semibold text-soft-brown">
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
          </article>
        ))}
      </div>
    </div>
  );
}

function SectionEditor({ section, draft, onSectionChange, onDraftChange, onSave }: {
  section: CookieSectionAdminResponse;
  draft: SectionDraft;
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
  onSave: () => void;
}) {
  const t = useTranslations("admin.cookies");
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

function TargetCard({ title, detail, selected, countLabel, gaps, onSelect }: { title: string; detail: string; selected: boolean; countLabel: string; gaps: AdminTranslationGap[]; onSelect: () => void }) {
  return (
    <article className={cn("rounded-brand border bg-admin-surface p-3 transition-colors", selected ? "border-admin-primary shadow-md" : "border-admin-border/45 hover:border-admin-accent")}>
      <button type="button" onClick={onSelect} className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface" aria-current={selected ? "true" : undefined}>
        <h3 className="truncate font-heading text-lg text-charcoal">{title}</h3>
        <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-soft-brown">{detail}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="rounded-pill border border-champagne-beige bg-warm-ivory px-2 py-1 text-xs font-semibold text-soft-brown">{countLabel}</span>
          <AdminTranslationGapButton gaps={gaps} label={`${title} translation gaps`} />
        </div>
      </button>
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
    <div className="space-y-4 rounded-brand border border-champagne-beige bg-warm-ivory p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-gold">{title}</h3>
      {children}
    </div>
  );
}

function PageFields({ page, suffix, onChange }: { page: CookiesPageAdminResponse; suffix: "en" | "bg"; onChange: (field: PageField, value: string) => void }) {
  const t = useTranslations("admin.cookies");
  const field = (name: string) => `${name}_${suffix}` as PageField;
  const gapProps = (name: string, label: string, en: string | null | undefined, bg: string | null | undefined) => suffix === "bg"
    ? { id: cookiesPageFieldId(name), label: <>{label}<MissingBgLabel show={isMissingTranslation(en, bg)} /></> }
    : { label };
  return (
    <div className="space-y-3">
      <TextInput {...gapProps("meta-title", t("metaTitle"), page.meta_title_en, page.meta_title_bg)} value={String(page[field("meta_title")] ?? "")} onChange={(value) => onChange(field("meta_title"), value)} />
      <TextArea {...gapProps("meta-description", t("metaDescription"), page.meta_description_en, page.meta_description_bg)} rows={3} value={String(page[field("meta_description")] ?? "")} onChange={(value) => onChange(field("meta_description"), value)} />
      <TextInput {...gapProps("eyebrow", t("eyebrow"), page.eyebrow_en, page.eyebrow_bg)} value={String(page[field("eyebrow")] ?? "")} onChange={(value) => onChange(field("eyebrow"), value)} />
      <TextInput {...gapProps("title", t("pageTitle"), page.title_en, page.title_bg)} value={String(page[field("title")] ?? "")} onChange={(value) => onChange(field("title"), value)} />
      <TextArea {...gapProps("subtitle", t("subtitleField"), page.subtitle_en, page.subtitle_bg)} rows={3} value={String(page[field("subtitle")] ?? "")} onChange={(value) => onChange(field("subtitle"), value)} />
      <TextInput {...gapProps("last-updated", t("lastUpdated"), page.last_updated_en, page.last_updated_bg)} value={String(page[field("last_updated")] ?? "")} onChange={(value) => onChange(field("last_updated"), value)} />
      <TextInput {...gapProps("inventory-title", t("inventoryTitle"), page.inventory_title_en, page.inventory_title_bg)} value={String(page[field("inventory_title")] ?? "")} onChange={(value) => onChange(field("inventory_title"), value)} />
      <TextInput {...gapProps("header-name", t("headerName"), page.header_name_en, page.header_name_bg)} value={String(page[field("header_name")] ?? "")} onChange={(value) => onChange(field("header_name"), value)} />
      <TextInput {...gapProps("header-purpose", t("headerPurpose"), page.header_purpose_en, page.header_purpose_bg)} value={String(page[field("header_purpose")] ?? "")} onChange={(value) => onChange(field("header_purpose"), value)} />
      <TextInput {...gapProps("header-type", t("headerType"), page.header_type_en, page.header_type_bg)} value={String(page[field("header_type")] ?? "")} onChange={(value) => onChange(field("header_type"), value)} />
      <TextInput {...gapProps("header-duration", t("headerDuration"), page.header_duration_en, page.header_duration_bg)} value={String(page[field("header_duration")] ?? "")} onChange={(value) => onChange(field("header_duration"), value)} />
    </div>
  );
}

function InventoryFields({ item, suffix }: { item: CookieInventoryAdminResponse; suffix: "en" | "bg" }) {
  const t = useTranslations("admin.cookies");
  const purpose = suffix === "bg" ? item.purpose_bg || item.purpose_en : item.purpose_en;
  const type = suffix === "bg" ? item.type_bg || item.type_en : item.type_en;
  const duration = suffix === "bg" ? item.duration_bg || item.duration_en : item.duration_en;
  const gapProps = (name: string, label: string, en: string, bg: string | null) => suffix === "bg"
    ? { id: cookieInventoryFieldId(item.name, name), label: <>{label}<MissingBgLabel show={isMissingTranslation(en, bg)} /></> }
    : { label };
  return (
    <div className="space-y-3 text-sm">
      <ReadOnlyField {...gapProps("purpose", t("purpose"), item.purpose_en, item.purpose_bg)} value={purpose} />
      <ReadOnlyField {...gapProps("type", t("type"), item.type_en, item.type_bg)} value={type} />
      <ReadOnlyField {...gapProps("duration", t("duration"), item.duration_en, item.duration_bg)} value={duration} />
    </div>
  );
}

function ReadOnlyField({ id, label, value }: { id?: string; label: ReactNode; value: string }) {
  return (
    <div id={id} tabIndex={id ? -1 : undefined}>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-gold">{label}</p>
      <p className="mt-1 break-words leading-6 text-charcoal">{value}</p>
    </div>
  );
}

function SectionFields({ section, draft, suffix, onSectionChange, onDraftChange }: {
  section: CookieSectionAdminResponse;
  draft: SectionDraft;
  suffix: "en" | "bg";
  onSectionChange: (field: SectionTextField, value: string) => void;
  onDraftChange: (field: keyof SectionDraft, value: string) => void;
}) {
  const t = useTranslations("admin.cookies");
  const titleField = `title_${suffix}` as SectionTextField;
  const bodyField = `body_${suffix}` as keyof SectionDraft;
  const gapProps = (name: string, label: string, en: string | null | undefined, bg: string | null | undefined) => suffix === "bg"
    ? { id: cookiesSectionFieldId(section.slug, name), label: <>{label}<MissingBgLabel show={isMissingTranslation(en, bg)} /></> }
    : { label };
  return (
    <div className="space-y-3">
      <TextInput {...gapProps("title", t("sectionTitle"), section.title_en, section.title_bg)} value={String(section[titleField] ?? "")} onChange={(value) => onSectionChange(titleField, value)} />
      <TextArea {...gapProps("body", t("body"), draft.body_en, draft.body_bg)} rows={8} value={draft[bodyField]} onChange={(value) => onDraftChange(bodyField, value)} />
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

function summarizeCookies(policy: CookiesAdminResponse | null, drafts: Record<string, SectionDraft>) {
  const sections = policy?.sections ?? [];
  const cookies = policy?.cookies ?? [];
  return {
    cookies: cookies.length,
    activeCookies: cookies.filter((item) => item.is_active).length,
    sections: sections.length,
    translationGaps:
      (policy ? pageTranslationGapCount(policy.page) : 0) +
      cookies.reduce((total, item) => total + cookieTranslationGapCount(item), 0) +
      sections.reduce((total, section) => total + sectionTranslationGapCount(section, drafts[section.slug] ?? sectionDraft(section)), 0),
  };
}

function pageTranslationGapCount(page: CookiesPageAdminResponse) {
  return cookiesPageTranslationGaps(page).length;
}

function cookieTranslationGapCount(item: CookieInventoryAdminResponse) {
  return cookieInventoryTranslationGaps(item).length;
}

function sectionTranslationGapCount(section: CookieSectionAdminResponse, draft: SectionDraft) {
  return cookieSectionTranslationGaps(section, draft).length;
}

function cookiesPageTranslationGaps(page: CookiesPageAdminResponse, onFix?: () => void): AdminTranslationGap[] {
  const fields: Array<[string, string, string | null | undefined, string | null | undefined]> = [
    ["meta-title", "Page > Meta title BG", page.meta_title_en, page.meta_title_bg],
    ["meta-description", "Page > Meta description BG", page.meta_description_en, page.meta_description_bg],
    ["eyebrow", "Page > Eyebrow BG", page.eyebrow_en, page.eyebrow_bg],
    ["title", "Page > Title BG", page.title_en, page.title_bg],
    ["subtitle", "Page > Subtitle BG", page.subtitle_en, page.subtitle_bg],
    ["last-updated", "Page > Last updated BG", page.last_updated_en, page.last_updated_bg],
    ["inventory-title", "Page > Inventory title BG", page.inventory_title_en, page.inventory_title_bg],
    ["header-name", "Page > Header name BG", page.header_name_en, page.header_name_bg],
    ["header-purpose", "Page > Header purpose BG", page.header_purpose_en, page.header_purpose_bg],
    ["header-type", "Page > Header type BG", page.header_type_en, page.header_type_bg],
    ["header-duration", "Page > Header duration BG", page.header_duration_en, page.header_duration_bg],
  ];
  return fields
    .filter(([, , en, bg]) => isMissingTranslation(en, bg))
    .map(([name, label]) => ({ id: `cookies-page-${name}`, label, fieldId: cookiesPageFieldId(name), onFix }));
}

function cookieInventoryTranslationGaps(item: CookieInventoryAdminResponse, onFix?: () => void): AdminTranslationGap[] {
  const fields: Array<[string, string, string | null | undefined, string | null | undefined]> = [
    ["purpose", `${item.name} > Purpose BG`, item.purpose_en, item.purpose_bg],
    ["type", `${item.name} > Type BG`, item.type_en, item.type_bg],
    ["duration", `${item.name} > Duration BG`, item.duration_en, item.duration_bg],
  ];
  return fields
    .filter(([, , en, bg]) => isMissingTranslation(en, bg))
    .map(([name, label]) => ({ id: `cookie-${item.name}-${name}`, label, fieldId: cookieInventoryFieldId(item.name, name), onFix }));
}

function cookieSectionTranslationGaps(section: CookieSectionAdminResponse, draft: SectionDraft, onFix?: () => void): AdminTranslationGap[] {
  const title = section.title_en || section.slug;
  const fields: Array<[string, string, string | null | undefined, string | null | undefined]> = [
    ["title", `${title} > Title BG`, section.title_en, section.title_bg],
    ["body", `${title} > Body BG`, draft.body_en, draft.body_bg],
  ];
  return fields
    .filter(([, , en, bg]) => isMissingTranslation(en, bg))
    .map(([name, label]) => ({ id: `cookies-${section.slug}-${name}`, label, fieldId: cookiesSectionFieldId(section.slug, name), onFix }));
}

function cookiesPageFieldId(name: string) {
  return `cookies-page-${name}-bg`;
}

function cookieInventoryFieldId(name: string, field: string) {
  return `cookies-inventory-${name}-${field}-bg`;
}

function cookiesSectionFieldId(slug: string, name: string) {
  return `cookies-${slug}-${name}-bg`;
}
