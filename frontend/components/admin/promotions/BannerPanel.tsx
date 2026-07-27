"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getAdminBanner, updateBanner } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { localInputToUtcIso, storedUtcToLocalInput } from "@/lib/datetime";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { BannerUpdateRequest } from "@/lib/types";

export function BannerPanel() {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();

  const [messageEn, setMessageEn] = useState("");
  const [messageBg, setMessageBg] = useState("");
  const [linkLabelEn, setLinkLabelEn] = useState("");
  const [linkLabelBg, setLinkLabelBg] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const b = await getAdminBanner();
      setMessageEn(b.message_en ?? "");
      setMessageBg(b.message_bg ?? "");
      setLinkLabelEn(b.link_label_en ?? "");
      setLinkLabelBg(b.link_label_bg ?? "");
      setLinkUrl(b.link_url ?? "");
      setEnabled(b.is_enabled);
      setStart(storedUtcToLocalInput(b.starts_at));
      setEnd(storedUtcToLocalInput(b.ends_at));
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("promotions.loadError"));
    } finally {
      setLoading(false);
    }
  }, [getLocalizedError, t]);

  useEffect(() => {
    load();
  }, [load]);

  // Clear the "saved" confirmation once the admin edits any field again.
  useEffect(() => {
    setSuccess(false);
  }, [messageEn, messageBg, linkLabelEn, linkLabelBg, linkUrl, enabled, start, end]);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (enabled && !messageEn.trim()) next.messageEn = t("promotions.bannerMessageRequired");
    if (start && end && new Date(start) >= new Date(end)) {
      next.window = t("promotions.windowInvalid");
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    if (!validate()) return;

    const payload: BannerUpdateRequest = {
      message_en: messageEn.trim() || null,
      message_bg: messageBg.trim() || null,
      link_label_en: linkLabelEn.trim() || null,
      link_label_bg: linkLabelBg.trim() || null,
      link_url: linkUrl.trim() || null,
      is_enabled: enabled,
      starts_at: localInputToUtcIso(start),
      ends_at: localInputToUtcIso(end),
    };
    setSaving(true);
    try {
      await updateBanner(payload);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("promotions.saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-soft-brown">{tCommon("loading")}</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl space-y-5">
      <h2 className="font-heading text-lg font-semibold text-charcoal">
        {t("promotions.topBanner")}
      </h2>

      {error && (
        <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-brand border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {t("promotions.bannerSaved")}
        </div>
      )}

      {/* Live preview */}
      <div>
        <p className="mb-1.5 text-sm font-medium text-soft-brown">{t("promotions.preview")}</p>
        {messageEn.trim() || messageBg.trim() ? (
          <div className="flex flex-wrap items-center justify-center gap-2 rounded-brand bg-charcoal px-4 py-2 text-center text-sm text-cream">
            <span>{messageEn || messageBg}</span>
            {linkUrl.trim() && (
              <span className="underline">{linkLabelEn || linkLabelBg || linkUrl}</span>
            )}
          </div>
        ) : (
          <p className="rounded-brand border border-dashed border-champagne-beige px-4 py-2 text-center text-sm text-soft-brown/60">
            {t("promotions.previewEmpty")}
          </p>
        )}
      </div>

      <label className="flex items-center gap-2 text-sm font-medium text-charcoal">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        {t("promotions.bannerEnabled")}
      </label>

      <Input
        label={t("promotions.messageEn")}
        value={messageEn}
        onChange={(e) => setMessageEn(e.target.value)}
        error={errors.messageEn}
        maxLength={500}
      />
      <Input
        label={`${t("promotions.messageBg")} (${t("optional")})`}
        value={messageBg}
        onChange={(e) => setMessageBg(e.target.value)}
        maxLength={500}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input
          label={`${t("promotions.linkLabelEn")} (${t("optional")})`}
          value={linkLabelEn}
          onChange={(e) => setLinkLabelEn(e.target.value)}
          maxLength={100}
        />
        <Input
          label={`${t("promotions.linkLabelBg")} (${t("optional")})`}
          value={linkLabelBg}
          onChange={(e) => setLinkLabelBg(e.target.value)}
          maxLength={100}
        />
      </div>
      <Input
        label={`${t("promotions.linkUrl")} (${t("optional")})`}
        value={linkUrl}
        onChange={(e) => setLinkUrl(e.target.value)}
        maxLength={2000}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="banner-start" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("promotions.startsAt")} <span className="text-soft-brown/60">({t("optional")})</span>
          </label>
          <input
            id="banner-start"
            type="datetime-local"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
          />
        </div>
        <div>
          <label htmlFor="banner-end" className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("promotions.endsAt")} <span className="text-soft-brown/60">({t("optional")})</span>
          </label>
          <input
            id="banner-end"
            type="datetime-local"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-soft-brown"
          />
        </div>
      </div>
      {errors.window && <p className="text-sm text-red-700">{errors.window}</p>}

      <Button type="submit" isLoading={saving}>
        {tCommon("save")}
      </Button>
    </form>
  );
}
