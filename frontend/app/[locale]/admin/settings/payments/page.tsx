"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { ApiError } from "@/lib/api-client";
import { getAdminPaymentSettings, updateAdminPaymentSettings } from "@/lib/api";
import type { PaymentSettingsResponse, PaymentSettingsUpdate } from "@/lib/types";

function toUpdate(settings: PaymentSettingsResponse): PaymentSettingsUpdate {
  return {
    card_payments_enabled: settings.card_payments_enabled,
    pay_on_delivery_enabled: settings.pay_on_delivery_enabled,
    pay_on_delivery_max_cents: settings.pay_on_delivery_max_cents,
  };
}

function centsToEuroInput(cents: number): string {
  return (cents / 100).toFixed(2);
}

function euroInputToCents(value: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(5000, Math.round(parsed * 100)));
}

export default function AdminPaymentSettingsPage() {
  const t = useTranslations("admin.paymentSettings");
  const [settings, setSettings] = useState<PaymentSettingsUpdate | null>(null);
  const [lastSaved, setLastSaved] = useState<PaymentSettingsUpdate | null>(null);
  const [stripe, setStripe] = useState<PaymentSettingsResponse["stripe"] | null>(null);
  const [codMaxInput, setCodMaxInput] = useState("50.00");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getAdminPaymentSettings()
      .then((response) => {
        if (cancelled) return;
        const next = toUpdate(response);
        setSettings(next);
        setLastSaved(next);
        setStripe(response.stripe);
        setCodMaxInput(centsToEuroInput(response.pay_on_delivery_max_cents));
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

  const bothDisabled = settings
    ? !settings.card_payments_enabled && !settings.pay_on_delivery_enabled
    : false;

  function updateSetting<K extends keyof PaymentSettingsUpdate>(
    key: K,
    value: PaymentSettingsUpdate[K]
  ) {
    setSaved(false);
    setError(null);
    setSettings((current) => (current ? { ...current, [key]: value } : current));
  }

  async function handleSave() {
    if (!settings) return;
    setSaved(false);
    setError(null);

    if (!settings.card_payments_enabled && !settings.pay_on_delivery_enabled) {
      setError(t("bothDisabledError"));
      return;
    }

    setIsSaving(true);
    try {
      const response = await updateAdminPaymentSettings(settings);
      const next = toUpdate(response);
      setSettings(next);
      setLastSaved(next);
      setStripe(response.stripe);
      setCodMaxInput(centsToEuroInput(response.pay_on_delivery_max_cents));
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-8 flex items-center gap-2">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
        <AdminInfoPopover content={t("subtitle")} />
      </div>

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-brand border border-champagne-beige bg-warm-ivory">
          <div className="flex items-center gap-2 border-b border-champagne-beige px-5 py-4">
            <h2 className="font-heading text-lg font-semibold text-charcoal">
              {t("stripeTitle")}
            </h2>
            <AdminInfoPopover content={t("stripeSubtitle")} />
          </div>

          {isLoading || !stripe ? (
            <p className="px-5 py-6 text-sm text-soft-brown">{t("loading")}</p>
          ) : (
            <div className="space-y-4 px-5 py-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-medium text-charcoal">{t("mode")}</span>
                <span className="rounded-pill bg-cream px-3 py-1 text-sm text-soft-brown">
                  {t(`modeValue.${stripe.mode}`)}
                </span>
                <span
                  className={
                    stripe.ready_for_card_payments
                      ? "rounded-pill bg-green-100 px-3 py-1 text-sm font-medium text-green-800"
                      : "rounded-pill bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800"
                  }
                >
                  {stripe.ready_for_card_payments ? t("ready") : t("notReady")}
                </span>
              </div>

              <dl className="grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-soft-brown">{t("secretKey")}</dt>
                  <dd className="font-medium text-charcoal">
                    {stripe.secret_key_configured ? t("configured") : t("missing")}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-soft-brown">{t("webhookSecret")}</dt>
                  <dd className="font-medium text-charcoal">
                    {stripe.webhook_secret_configured ? t("configured") : t("missing")}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-soft-brown">{t("publishableKey")}</dt>
                  <dd className="font-medium text-charcoal">
                    {stripe.publishable_key_configured ? t("configured") : t("missing")}
                  </dd>
                </div>
              </dl>

              {stripe.problems.length > 0 && (
                <div className="rounded-brand border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  <p className="font-semibold">{t("problemsTitle")}</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {stripe.problems.map((problem) => (
                      <li key={problem}>{problem}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="rounded-brand border border-champagne-beige bg-warm-ivory">
          <div className="flex items-center gap-2 border-b border-champagne-beige px-5 py-4">
            <h2 className="font-heading text-lg font-semibold text-charcoal">
              {t("methodsTitle")}
            </h2>
            <AdminInfoPopover content={t("methodsSubtitle")} />
          </div>

          {isLoading || !settings ? (
            <p className="px-5 py-6 text-sm text-soft-brown">{t("loading")}</p>
          ) : (
            <div>
              <div className="divide-y divide-champagne-beige">
                <label className="flex cursor-pointer items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-cream/60">
                  <span>
                    <span className="block text-sm font-semibold text-charcoal">
                      {t("cardTitle")}
                    </span>
                    <span className="mt-1 block text-xs text-soft-brown">
                      {settings.card_payments_enabled ? t("enabled") : t("disabled")}
                    </span>
                  </span>
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-muted-gold"
                    checked={settings.card_payments_enabled}
                    onChange={(event) =>
                      updateSetting("card_payments_enabled", event.target.checked)
                    }
                  />
                </label>

                <label className="flex cursor-pointer items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-cream/60">
                  <span>
                    <span className="block text-sm font-semibold text-charcoal">
                      {t("codTitle")}
                    </span>
                    <span className="mt-1 block text-xs text-soft-brown">
                      {settings.pay_on_delivery_enabled ? t("enabled") : t("disabled")}
                    </span>
                  </span>
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-muted-gold"
                    checked={settings.pay_on_delivery_enabled}
                    onChange={(event) =>
                      updateSetting("pay_on_delivery_enabled", event.target.checked)
                    }
                  />
                </label>
              </div>

              <div className="border-t border-champagne-beige px-5 py-4">
                <div className="flex items-center gap-2">
                  <label className="block text-sm font-semibold text-charcoal" htmlFor="cod-max">
                    {t("codMaxLabel")}
                  </label>
                  <AdminInfoPopover content={t("codMaxHint")} />
                </div>
                <div className="mt-2 flex max-w-xs items-center gap-2">
                  <span className="text-sm text-soft-brown">EUR</span>
                  <input
                    id="cod-max"
                    type="number"
                    min="0"
                    max="50"
                    step="0.01"
                    value={codMaxInput}
                    onChange={(event) => {
                      const value = event.target.value;
                      setCodMaxInput(value);
                      updateSetting("pay_on_delivery_max_cents", euroInputToCents(value));
                    }}
                    onBlur={() => {
                      if (settings) {
                        setCodMaxInput(centsToEuroInput(settings.pay_on_delivery_max_cents));
                      }
                    }}
                    className="h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 border-t border-champagne-beige px-5 py-4">
            {bothDisabled && <span className="text-xs text-red-700">{t("bothDisabledShort")}</span>}
            {isDirty && !bothDisabled && <span className="text-xs text-soft-brown">{t("unsaved")}</span>}
            <Button
              type="button"
              onClick={handleSave}
              disabled={!settings || !isDirty}
              isLoading={isSaving}
            >
              {t("save")}
            </Button>
          </div>
        </section>
      </div>

      {saved && <SaveConfirmation message={t("saved")} onDismiss={() => setSaved(false)} />}
    </div>
  );
}
