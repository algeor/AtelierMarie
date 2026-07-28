"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  createFaqItem,
  deleteFaqItem,
  getAdminFaq,
  reorderFaqItems,
  updateFaqItem,
  updateFaqSection,
} from "@/lib/api";
import type {
  FaqAdminResponse,
  FaqItemAdminResponse,
  FaqSectionAdminResponse,
} from "@/lib/types";

type Draft = {
  question_en: string;
  question_bg: string;
  answer_en: string;
  answer_bg: string;
};

const EMPTY_DRAFT: Draft = {
  question_en: "",
  question_bg: "",
  answer_en: "",
  answer_bg: "",
};

export function FaqManager() {
  const t = useTranslations("admin.faq");
  const [faq, setFaq] = useState<FaqAdminResponse | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    getAdminFaq()
      .then((data) => {
        if (!cancelled) setFaq(data);
      })
      .catch(() => {
        if (!cancelled) setError(t("loadError"));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  function replaceSection(section: FaqSectionAdminResponse) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((candidate) =>
              candidate.slug === section.slug ? section : candidate
            ),
          }
        : current
    );
  }

  function replaceItem(item: FaqItemAdminResponse) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((section) => ({
              ...section,
              items: section.items.map((candidate) =>
                candidate.id === item.id ? item : candidate
              ),
            })),
          }
        : current
    );
  }

  function updateItemField(
    itemId: number,
    field: keyof Draft,
    value: string
  ) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((section) => ({
              ...section,
              items: section.items.map((item) =>
                item.id === itemId ? { ...item, [field]: value } : item
              ),
            })),
          }
        : current
    );
  }

  function updateSectionField(
    slug: string,
    field: "title_en" | "title_bg" | "icon",
    value: string
  ) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((section) =>
              section.slug === slug ? { ...section, [field]: value } : section
            ),
          }
        : current
    );
  }

  async function saveSection(section: FaqSectionAdminResponse) {
    setError(null);
    try {
      replaceSection(
        await updateFaqSection(section.slug, {
          title_en: section.title_en,
          title_bg: section.title_bg || null,
          icon: section.icon || null,
          sort_order: section.sort_order,
        })
      );
    } catch {
      setError(t("saveError"));
    }
  }

  async function saveItem(item: FaqItemAdminResponse) {
    const key = `item-${item.id}`;
    if (!item.question_en.trim()) {
      setValidation({ [key]: t("questionEnRequired") });
      return;
    }
    if (!item.answer_en.trim()) {
      setValidation({ [key]: t("answerEnRequired") });
      return;
    }
    setValidation({});
    setError(null);
    try {
      replaceItem(
        await updateFaqItem(item.id, {
          question_en: item.question_en,
          question_bg: item.question_bg || null,
          answer_en: item.answer_en,
          answer_bg: item.answer_bg || null,
          is_published: item.is_published,
          sort_order: item.sort_order,
        })
      );
    } catch {
      setError(t("saveError"));
    }
  }

  async function togglePublished(item: FaqItemAdminResponse) {
    try {
      replaceItem(await updateFaqItem(item.id, { is_published: !item.is_published }));
    } catch {
      setError(t("saveError"));
    }
  }

  async function removeItem(itemId: number) {
    setError(null);
    try {
      await deleteFaqItem(itemId);
      setFaq((current) =>
        current
          ? {
              sections: current.sections.map((section) => ({
                ...section,
                items: section.items.filter((item) => item.id !== itemId),
              })),
            }
          : current
      );
    } catch {
      setError(t("saveError"));
    }
  }

  async function moveItem(section: FaqSectionAdminResponse, itemId: number, delta: -1 | 1) {
    const index = section.items.findIndex((item) => item.id === itemId);
    const nextIndex = index + delta;
    if (index < 0 || nextIndex < 0 || nextIndex >= section.items.length) return;
    const ordered = [...section.items];
    const [item] = ordered.splice(index, 1);
    ordered.splice(nextIndex, 0, item!);
    try {
      setFaq(await reorderFaqItems({ section: section.slug, ordered_ids: ordered.map((item) => item.id) }));
    } catch {
      setError(t("saveError"));
    }
  }

  async function createItem(sectionSlug: string) {
    const draft = drafts[sectionSlug] ?? EMPTY_DRAFT;
    const key = `new-${sectionSlug}`;
    if (!draft.question_en.trim()) {
      setValidation({ [key]: t("questionEnRequired") });
      return;
    }
    if (!draft.answer_en.trim()) {
      setValidation({ [key]: t("answerEnRequired") });
      return;
    }
    setValidation({});
    try {
      const item = await createFaqItem({
        section: sectionSlug,
        question_en: draft.question_en,
        question_bg: draft.question_bg || null,
        answer_en: draft.answer_en,
        answer_bg: draft.answer_bg || null,
      });
      setFaq((current) =>
        current
          ? {
              sections: current.sections.map((section) =>
                section.slug === sectionSlug
                  ? { ...section, items: [...section.items, item] }
                  : section
              ),
            }
          : current
      );
      setDrafts((current) => ({ ...current, [sectionSlug]: EMPTY_DRAFT }));
    } catch {
      setError(t("saveError"));
    }
  }

  if (!faq && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="space-y-6">
      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {faq?.sections.map((section) => (
        <section key={section.slug} className="rounded-brand border border-champagne-beige bg-cream p-5">
          <div className="grid gap-4 md:grid-cols-[1fr_1fr_96px_auto] md:items-end">
            <label className="text-sm font-medium text-charcoal">
              {t("titleEn")}
              <input
                value={section.title_en}
                onChange={(event) => updateSectionField(section.slug, "title_en", event.target.value)}
                className="mt-1 w-full rounded-brand border border-champagne-beige bg-white px-3 py-2 text-sm text-charcoal"
              />
            </label>
            <label className="text-sm font-medium text-charcoal">
              {t("titleBg")}
              <input
                value={section.title_bg ?? ""}
                onChange={(event) => updateSectionField(section.slug, "title_bg", event.target.value)}
                className="mt-1 w-full rounded-brand border border-champagne-beige bg-white px-3 py-2 text-sm text-charcoal"
              />
            </label>
            <label className="text-sm font-medium text-charcoal">
              {t("icon")}
              <input
                value={section.icon ?? ""}
                onChange={(event) => updateSectionField(section.slug, "icon", event.target.value)}
                className="mt-1 w-full rounded-brand border border-champagne-beige bg-white px-3 py-2 text-sm text-charcoal"
              />
            </label>
            <button
              type="button"
              onClick={() => saveSection(section)}
              className="min-h-[42px] rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white"
            >
              {t("saveSection")}
            </button>
          </div>

          <div className="mt-5 space-y-4">
            {section.items.length === 0 && <p className="text-sm text-soft-brown">{t("empty")}</p>}
            {section.items.map((item, index) => (
              <ItemEditor
                key={item.id}
                item={item}
                error={validation[`item-${item.id}`]}
                onChange={updateItemField}
                onSave={saveItem}
                onDelete={removeItem}
                onToggle={togglePublished}
                onMoveUp={() => moveItem(section, item.id, -1)}
                onMoveDown={() => moveItem(section, item.id, 1)}
                disableUp={index === 0}
                disableDown={index === section.items.length - 1}
              />
            ))}
          </div>

          <NewItemForm
            sectionSlug={section.slug}
            draft={drafts[section.slug] ?? EMPTY_DRAFT}
            error={validation[`new-${section.slug}`]}
            onChange={(field, value) =>
              setDrafts((current) => ({
                ...current,
                [section.slug]: { ...(current[section.slug] ?? EMPTY_DRAFT), [field]: value },
              }))
            }
            onCreate={() => createItem(section.slug)}
          />
        </section>
      ))}
    </div>
  );
}

function ItemEditor({
  item,
  error,
  onChange,
  onSave,
  onDelete,
  onToggle,
  onMoveUp,
  onMoveDown,
  disableUp,
  disableDown,
}: {
  item: FaqItemAdminResponse;
  error?: string;
  onChange: (itemId: number, field: keyof Draft, value: string) => void;
  onSave: (item: FaqItemAdminResponse) => void;
  onDelete: (itemId: number) => void;
  onToggle: (item: FaqItemAdminResponse) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  disableUp: boolean;
  disableDown: boolean;
}) {
  const t = useTranslations("admin.faq");
  return (
    <div className="rounded-brand border border-champagne-beige bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-pill bg-champagne-beige/60 px-3 py-1 text-xs font-medium text-soft-brown">
          {item.is_published ? t("published") : t("hidden")}
        </span>
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={disableUp} onClick={onMoveUp} className="rounded-brand border border-champagne-beige px-3 py-2 text-xs text-soft-brown disabled:opacity-40">
            {t("moveUp")}
          </button>
          <button type="button" disabled={disableDown} onClick={onMoveDown} className="rounded-brand border border-champagne-beige px-3 py-2 text-xs text-soft-brown disabled:opacity-40">
            {t("moveDown")}
          </button>
          <button type="button" onClick={() => onToggle(item)} className="rounded-brand border border-champagne-beige px-3 py-2 text-xs text-soft-brown">
            {item.is_published ? t("hide") : t("show")}
          </button>
          <button type="button" onClick={() => onDelete(item.id)} className="rounded-brand border border-red-200 px-3 py-2 text-xs text-red-700">
            {t("deleteItem")}
          </button>
        </div>
      </div>
      <EditorFields
        values={{
          question_en: item.question_en,
          question_bg: item.question_bg ?? "",
          answer_en: item.answer_en,
          answer_bg: item.answer_bg ?? "",
        }}
        onChange={(field, value) => onChange(item.id, field, value)}
      />
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      <button type="button" onClick={() => onSave(item)} className="mt-3 rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white">
        {t("saveItem")}
      </button>
    </div>
  );
}

function NewItemForm({
  draft,
  error,
  onChange,
  onCreate,
}: {
  sectionSlug: string;
  draft: Draft;
  error?: string;
  onChange: (field: keyof Draft, value: string) => void;
  onCreate: () => void;
}) {
  const t = useTranslations("admin.faq");
  return (
    <div className="mt-5 border-t border-champagne-beige pt-5">
      <h3 className="font-heading text-lg text-charcoal">{t("newItem")}</h3>
      <div className="mt-3">
        <EditorFields values={draft} onChange={onChange} />
      </div>
      {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
      <button type="button" onClick={onCreate} className="mt-3 rounded-brand bg-muted-gold px-4 py-2 text-sm font-medium text-white">
        {t("createItem")}
      </button>
    </div>
  );
}

function EditorFields({
  values,
  onChange,
}: {
  values: Draft;
  onChange: (field: keyof Draft, value: string) => void;
}) {
  const t = useTranslations("admin.faq");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="space-y-3">
        <label className="block text-sm font-medium text-charcoal">
          {t("questionEn")}
          <input value={values.question_en} onChange={(event) => onChange("question_en", event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige px-3 py-2 text-sm" />
        </label>
        <label className="block text-sm font-medium text-charcoal">
          {t("answerEn")}
          <textarea value={values.answer_en} rows={5} onChange={(event) => onChange("answer_en", event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige px-3 py-2 text-sm" />
        </label>
      </div>
      <div className="space-y-3">
        <label className="block text-sm font-medium text-charcoal">
          {t("questionBg")}
          <input value={values.question_bg} onChange={(event) => onChange("question_bg", event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige px-3 py-2 text-sm" />
        </label>
        <label className="block text-sm font-medium text-charcoal">
          {t("answerBg")}
          <textarea value={values.answer_bg} rows={5} onChange={(event) => onChange("answer_bg", event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige px-3 py-2 text-sm" />
        </label>
      </div>
    </div>
  );
}
