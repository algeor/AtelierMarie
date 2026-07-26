"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api-client";
import {
  createTaxonomyTerm,
  deleteTaxonomyTerm,
  getAdminTaxonomy,
  updateTaxonomyTerm,
} from "@/lib/api";
import { useLocalizedError } from "@/lib/useLocalizedError";
import type { AdminTaxonomyTerm, TaxonomyKind } from "@/lib/types";

interface TaxonomyManagerProps {
  kind: TaxonomyKind;
}

/**
 * CRUD manager for one taxonomy kind (product types, categories, or labels).
 * Sourced entirely from the taxonomy API — no hardcoded term lists.
 */
export function TaxonomyManager({ kind }: TaxonomyManagerProps) {
  const t = useTranslations("admin");
  const getLocalizedError = useLocalizedError();
  const [terms, setTerms] = useState<AdminTaxonomyTerm[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newNameEn, setNewNameEn] = useState("");
  const [newNameBg, setNewNameBg] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isReordering, setIsReordering] = useState(false);

  async function refresh() {
    try {
      setTerms(await getAdminTaxonomy(kind));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.loadError"));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    setIsLoading(true);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  async function handleCreate() {
    if (!newNameEn.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      await createTaxonomyTerm(kind, {
        name_en: newNameEn.trim(),
        name_bg: newNameBg.trim() || null,
        sort_order: terms.length,
      });
      setNewNameEn("");
      setNewNameBg("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
    } finally {
      setIsCreating(false);
    }
  }

  async function patch(slug: string, data: Parameters<typeof updateTaxonomyTerm>[2]) {
    setError(null);
    try {
      await updateTaxonomyTerm(kind, slug, data);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
    }
  }

  async function handleRename(term: AdminTaxonomyTerm) {
    const nextEn = window.prompt(t("taxonomy.renameEnPrompt"), term.name_en);
    if (nextEn === null || !nextEn.trim()) return;
    const nextBg = window.prompt(t("taxonomy.renameBgPrompt"), term.name_bg ?? "");
    const data: Parameters<typeof updateTaxonomyTerm>[2] = { name_en: nextEn.trim() };
    // Cancelling the BG prompt (null) leaves name_bg unchanged; only an
    // explicit empty string clears it.
    if (nextBg !== null) data.name_bg = nextBg.trim() || null;
    await patch(term.slug, data);
  }

  async function handleReorder(index: number, direction: -1 | 1) {
    const other = index + direction;
    if (other < 0 || other >= terms.length || isReordering) return;
    const a = terms[index];
    const b = terms[other];
    if (!a || !b) return;
    setIsReordering(true);
    setError(null);
    try {
      // If both share a sort_order, synthesize a gap so the swap is observable.
      const aOrder = a.sort_order;
      const bOrder = b.sort_order === a.sort_order ? a.sort_order + direction : b.sort_order;
      // Apply both updates, then refresh once (avoids the transient mid-swap
      // state a per-call refresh would render).
      await updateTaxonomyTerm(kind, a.slug, { sort_order: bOrder });
      await updateTaxonomyTerm(kind, b.slug, { sort_order: aOrder });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
      await refresh(); // resync after a partial failure
    } finally {
      setIsReordering(false);
    }
  }

  async function handleDelete(term: AdminTaxonomyTerm) {
    if (!window.confirm(t("taxonomy.deleteConfirm", { name: term.name_en }))) return;
    setError(null);
    try {
      await deleteTaxonomyTerm(kind, term.slug);
      await refresh();
    } catch (err) {
      if (err instanceof ApiError && err.code === "TAXONOMY_IN_USE") {
        setError(t("taxonomy.inUse", { name: term.name_en }));
        return;
      }
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
    }
  }

  if (isLoading) {
    return <p className="text-sm text-soft-brown">{t("taxonomy.loading")}</p>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Create form */}
      <div className="flex flex-wrap items-end gap-3 rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <div className="w-48">
          <Input
            label={t("taxonomy.nameEn")}
            value={newNameEn}
            onChange={(e) => setNewNameEn(e.target.value)}
          />
        </div>
        <div className="w-48">
          <Input
            label={t("taxonomy.nameBg")}
            value={newNameBg}
            onChange={(e) => setNewNameBg(e.target.value)}
          />
        </div>
        <Button type="button" onClick={handleCreate} isLoading={isCreating} disabled={!newNameEn.trim()}>
          {t("taxonomy.add")}
        </Button>
      </div>

      {/* Term list */}
      {terms.length === 0 ? (
        <p className="text-sm text-soft-brown">{t("taxonomy.empty")}</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-champagne-beige text-left text-soft-brown">
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colName")}</th>
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colSlug")}</th>
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colCount")}</th>
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colStatus")}</th>
              <th className="py-2 font-medium">{t("taxonomy.colActions")}</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((term, index) => (
              <tr key={term.slug} className="border-b border-champagne-beige/60">
                <td className="py-2 pr-3 text-charcoal">
                  {term.name_en}
                  {term.name_bg ? <span className="text-soft-brown/70"> / {term.name_bg}</span> : null}
                </td>
                <td className="py-2 pr-3 font-mono text-xs text-soft-brown">{term.slug}</td>
                <td className="py-2 pr-3 text-soft-brown">{term.product_count}</td>
                <td className="py-2 pr-3">
                  <span
                    className={
                      term.is_active
                        ? "rounded-pill bg-green-100 px-2 py-0.5 text-xs text-green-800"
                        : "rounded-pill bg-champagne-beige px-2 py-0.5 text-xs text-soft-brown"
                    }
                  >
                    {term.is_active ? t("taxonomy.active") : t("taxonomy.inactive")}
                  </span>
                </td>
                <td className="flex flex-wrap gap-1.5 py-2">
                  <Button type="button" variant="ghost" onClick={() => handleReorder(index, -1)} disabled={index === 0 || isReordering}>
                    ↑
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => handleReorder(index, 1)} disabled={index === terms.length - 1 || isReordering}>
                    ↓
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => handleRename(term)}>
                    {t("taxonomy.rename")}
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => patch(term.slug, { is_active: !term.is_active })}>
                    {term.is_active ? t("taxonomy.deactivate") : t("taxonomy.activate")}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => handleDelete(term)} disabled={term.product_count > 0}>
                    {t("taxonomy.delete")}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
