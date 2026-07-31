"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { getAdminDeliverySettings, updateAdminDeliverySettings } from "@/lib/api";
import type { DeliverySettingsResponse, DeliverySettingsUpdate } from "@/lib/types";

type ToggleKey = keyof DeliverySettingsUpdate;

const TOGGLES: Array<{
  key: ToggleKey;
  courier: "speedy" | "econt";
  method: "office" | "door";
}> = [
  { key: "speedy_office_enabled", courier: "speedy", method: "office" },
  { key: "speedy_door_enabled", courier: "speedy", method: "door" },
  { key: "econt_office_enabled", courier: "econt", method: "office" },
  { key: "econt_door_enabled", courier: "econt", method: "door" },
];

function toUpdate(settings: DeliverySettingsResponse): DeliverySettingsUpdate {
  return {
    speedy_office_enabled: settings.speedy_office_enabled,
    speedy_door_enabled: settings.speedy_door_enabled,
    econt_office_enabled: settings.econt_office_enabled,
    econt_door_enabled: settings.econt_door_enabled,
  };
}

export default function AdminDeliveryPage() {
  const t = useTranslations("admin.delivery");
  const [settings, setSettings] = useState<DeliverySettingsUpdate | null>(null);
  const [lastSaved, setLastSaved] = useState<DeliverySettingsUpdate | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getAdminDeliverySettings()
      .then((response) => {
        if (cancelled) return;
        const next = toUpdate(response);
        setSettings(next);
        setLastSaved(next);
        setUpdatedAt(response.updated_at);
      })
      .catch(() => {
        if (!cancelled) setError(t("loadError"));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  const isDirty = useMemo(
    () => JSON.stringify(settings) !== JSON.stringify(lastSaved),
    [settings, lastSaved],
  );

  const enabledCount = settings
    ? TOGGLES.filter((toggle) => settings[toggle.key]).length
    : 0;

  async function handleSave() {
    if (!settings) return;
    setError(null);
    setSaved(false);
    setIsSaving(true);
    try {
      const response = await updateAdminDeliverySettings(settings);
      const next = toUpdate(response);
      setSettings(next);
      setLastSaved(next);
      setUpdatedAt(response.updated_at);
      setSaved(true);
    } catch {
      setError(t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
        <p className="mt-1 text-sm text-soft-brown">{t("subtitle")}</p>
      </div>

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 rounded-brand border border-champagne-beige bg-warm-ivory p-5">
        <h2 className="font-heading text-lg font-semibold text-charcoal">
          {t("pricingTitle")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-soft-brown">{t("pricingBody")}</p>
      </div>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory">
        <div className="flex flex-col gap-2 border-b border-champagne-beige px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-heading text-lg font-semibold text-charcoal">
              {t("methodsTitle")}
            </h2>
            <p className="mt-1 text-sm text-soft-brown">
              {t("enabledSummary", { count: enabledCount, total: TOGGLES.length })}
            </p>
          </div>
          {updatedAt && <p className="text-xs text-soft-brown">{t("updatedAt", { updatedAt })}</p>}
        </div>

        {isLoading || !settings ? (
          <p className="px-5 py-6 text-sm text-soft-brown">{t("loading")}</p>
        ) : (
          <div className="divide-y divide-champagne-beige">
            {TOGGLES.map((toggle) => {
              const enabled = settings[toggle.key];
              return (
                <label
                  key={toggle.key}
                  className="flex cursor-pointer items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-cream/60"
                >
                  <span>
                    <span className="block text-sm font-semibold text-charcoal">
                      {t(`courier.${toggle.courier}`)} · {t(`method.${toggle.method}`)}
                    </span>
                    <span className="mt-1 block text-xs text-soft-brown">
                      {enabled ? t("enabled") : t("disabled")}
                    </span>
                  </span>
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-muted-gold"
                    checked={enabled}
                    onChange={(event) => {
                      setSaved(false);
                      setSettings((current) =>
                        current ? { ...current, [toggle.key]: event.target.checked } : current,
                      );
                    }}
                  />
                </label>
              );
            })}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 border-t border-champagne-beige px-5 py-4">
          {isDirty && <span className="text-xs text-soft-brown">{t("unsaved")}</span>}
          <Button type="button" onClick={handleSave} disabled={!settings || !isDirty} isLoading={isSaving}>
            {t("save")}
          </Button>
        </div>
      </div>

      {saved && <SaveConfirmation message={t("saved")} onDismiss={() => setSaved(false)} />}
    </div>
  );
}
