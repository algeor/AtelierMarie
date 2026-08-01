"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  getEcontSettings,
  testEcontConnection,
  updateEcontSettings,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  EcontConnectionTestResponse,
  EcontSettingsResponse,
  EcontSettingsUpdate,
} from "@/lib/types";

type FormState = Required<
  Pick<
    EcontSettingsUpdate,
    | "enabled"
    | "environment"
    | "shop_id"
    | "credential_source"
    | "sender_delivery_mode"
    | "sender_office_code"
    | "sender_city"
    | "sender_post_code"
    | "sender_address"
    | "sender_quarter"
    | "sender_street"
    | "sender_num"
    | "sender_other"
    | "default_pack_count"
    | "shipment_description"
    | "declared_value_enabled"
    | "default_payment_side"
    | "courier_currency"
    | "currency_conversion_rate"
    | "office_locator_enabled"
  >
>;

const STRING_FIELDS: (keyof FormState)[] = [
  "shop_id",
  "sender_office_code",
  "sender_city",
  "sender_post_code",
  "sender_address",
  "sender_quarter",
  "sender_street",
  "sender_num",
  "sender_other",
  "shipment_description",
];

function toForm(settings: EcontSettingsResponse): FormState {
  return {
    enabled: settings.enabled,
    environment: settings.environment,
    shop_id: settings.shop_id ?? "",
    credential_source: settings.credential_source,
    sender_delivery_mode: settings.sender_delivery_mode,
    sender_office_code: settings.sender_office_code ?? "",
    sender_city: settings.sender_city ?? "",
    sender_post_code: settings.sender_post_code ?? "",
    sender_address: settings.sender_address ?? "",
    sender_quarter: settings.sender_quarter ?? "",
    sender_street: settings.sender_street ?? "",
    sender_num: settings.sender_num ?? "",
    sender_other: settings.sender_other ?? "",
    default_pack_count: settings.default_pack_count,
    shipment_description: settings.shipment_description,
    declared_value_enabled: settings.declared_value_enabled,
    default_payment_side: settings.default_payment_side,
    courier_currency: settings.courier_currency,
    currency_conversion_rate: settings.currency_conversion_rate,
    office_locator_enabled: settings.office_locator_enabled,
  };
}

function toPayload(form: FormState): EcontSettingsUpdate {
  const payload = { ...form } as Record<string, unknown>;
  for (const key of STRING_FIELDS) {
    const value = payload[key];
    if (typeof value === "string") {
      payload[key] = value.trim() || null;
    }
  }
  payload.default_pack_count = Number(form.default_pack_count);
  payload.currency_conversion_rate = form.currency_conversion_rate
    ? Number(form.currency_conversion_rate)
    : null;
  return payload as EcontSettingsUpdate;
}

export default function AdminEcontSettingsPage() {
  const t = useTranslations("admin.econt");
  const getLocalizedError = useLocalizedError();
  const [settings, setSettings] = useState<EcontSettingsResponse | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<EcontConnectionTestResponse | null>(null);

  useEffect(() => {
    getEcontSettings()
      .then((data) => {
        setSettings(data);
        setForm(toForm(data));
      })
      .catch((err) => {
        setError(err instanceof ApiError ? getLocalizedError(err.code) : t("loadError"));
      })
      .finally(() => setIsLoading(false));
  }, [getLocalizedError, t]);

  const initialForm = useMemo(() => (settings ? toForm(settings) : null), [settings]);
  const isDirty = Boolean(form && initialForm && JSON.stringify(form) !== JSON.stringify(initialForm));

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setValidationError(null);
    setSuccess(null);
    setForm((current) => (current ? { ...current, [key]: value } : current));
  }

  function validate(current: FormState): string | null {
    if (!current.shipment_description.trim()) return t("validation.descriptionRequired");
    if (Number(current.default_pack_count) < 1 || Number(current.default_pack_count) > 99) {
      return t("validation.packCountRange");
    }
    return null;
  }

  async function handleSave() {
    if (!form) return;
    const invalid = validate(form);
    if (invalid) {
      setValidationError(invalid);
      return;
    }
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateEcontSettings(toPayload(form));
      setSettings(updated);
      setForm(toForm(updated));
      setSuccess(t("saveSuccess"));
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleTestConnection() {
    setIsTesting(true);
    setError(null);
    setTestResult(null);
    try {
      const result = await testEcontConnection();
      setTestResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("testError"));
    } finally {
      setIsTesting(false);
    }
  }

  if (isLoading) {
    return (
      <div>
        <Skeleton className="mb-6 h-8 w-56" />
        <div className="space-y-4 rounded-brand border border-champagne-beige bg-cream p-6">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-2/3" />
        </div>
      </div>
    );
  }

  if (!form || !settings) return null;

  const statusClass = testResult?.ok
    ? "border-green-200 bg-green-50 text-green-800"
    : "border-amber-200 bg-amber-50 text-amber-800";

  return (
    <div className="max-w-5xl">
      <div className="mb-8 flex items-center gap-2">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
      </div>

      {(error || validationError || success) && (
        <div
          className={cn(
            "mb-6 rounded-brand border p-4 text-sm",
            success
              ? "border-green-200 bg-green-50 text-green-800"
              : "border-red-200 bg-red-50 text-red-700",
          )}
          role="status"
        >
          {success ?? validationError ?? error}
        </div>
      )}

      <div className="space-y-6">
        <section className="rounded-brand border border-champagne-beige bg-cream p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase text-soft-brown">
            {t("sections.integration")}
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Toggle
              label={t("fields.enabled")}
              checked={form.enabled}
              onChange={(value) => setField("enabled", value)}
            />
            <Field label={t("fields.environment")}>
              <select
                value={form.environment}
                onChange={(event) => setField("environment", event.target.value as FormState["environment"])}
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              >
                <option value="demo">{t("options.demo")}</option>
                <option value="production">{t("options.production")}</option>
              </select>
            </Field>
            <Field label={t("fields.shopId")}>
              <input
                value={form.shop_id ?? ""}
                onChange={(event) => setField("shop_id", event.target.value)}
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              />
            </Field>
            <Field label={t("fields.credentialSource")}>
              <select
                value={form.credential_source}
                onChange={(event) =>
                  setField("credential_source", event.target.value as FormState["credential_source"])
                }
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              >
                <option value="env">{t("options.env")}</option>
              </select>
            </Field>
          </div>

          <dl className="mt-5 grid gap-3 rounded-brand border border-champagne-beige bg-warm-ivory p-4 text-sm sm:grid-cols-3">
            <CredentialState label={t("fields.privateKey")} value={settings.secret_state.private_key_configured} />
            <CredentialState label={t("fields.shopIdConfigured")} value={settings.secret_state.shop_id_configured} />
            <CredentialState label={t("fields.encryptionKey")} value={settings.secret_state.encryption_key_configured} />
          </dl>
        </section>

        <section className="rounded-brand border border-champagne-beige bg-cream p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase text-soft-brown">
            {t("sections.sender")}
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label={t("fields.senderMode")}>
              <select
                value={form.sender_delivery_mode}
                onChange={(event) =>
                  setField("sender_delivery_mode", event.target.value as FormState["sender_delivery_mode"])
                }
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              >
                <option value="office">{t("options.office")}</option>
                <option value="door">{t("options.door")}</option>
              </select>
            </Field>
            <TextInput label={t("fields.senderOfficeCode")} value={form.sender_office_code} onChange={(value) => setField("sender_office_code", value)} />
            <TextInput label={t("fields.senderCity")} value={form.sender_city} onChange={(value) => setField("sender_city", value)} />
            <TextInput label={t("fields.senderPostCode")} value={form.sender_post_code} onChange={(value) => setField("sender_post_code", value)} />
            <TextInput label={t("fields.senderStreet")} value={form.sender_street} onChange={(value) => setField("sender_street", value)} />
            <TextInput label={t("fields.senderNum")} value={form.sender_num} onChange={(value) => setField("sender_num", value)} />
            <TextInput label={t("fields.senderQuarter")} value={form.sender_quarter} onChange={(value) => setField("sender_quarter", value)} />
            <TextInput label={t("fields.senderOther")} value={form.sender_other} onChange={(value) => setField("sender_other", value)} />
            <TextInput label={t("fields.senderAddress")} value={form.sender_address} onChange={(value) => setField("sender_address", value)} />
          </div>
        </section>

        <section className="rounded-brand border border-champagne-beige bg-cream p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase text-soft-brown">
            {t("sections.defaults")}
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label={t("fields.packCount")}>
              <input
                type="number"
                min={1}
                max={99}
                value={form.default_pack_count}
                onChange={(event) => setField("default_pack_count", Number(event.target.value))}
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              />
            </Field>
            <TextInput label={t("fields.description")} value={form.shipment_description} onChange={(value) => setField("shipment_description", value)} />
            <Field label={t("fields.paymentSide")}>
              <select
                value={form.default_payment_side}
                onChange={(event) =>
                  setField("default_payment_side", event.target.value as FormState["default_payment_side"])
                }
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              >
                <option value="sender">{t("options.sender")}</option>
                <option value="receiver">{t("options.receiver")}</option>
              </select>
            </Field>
            <Field label={t("fields.currency")}>
              <select
                value={form.courier_currency}
                onChange={(event) => setField("courier_currency", event.target.value as FormState["courier_currency"])}
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              >
                <option value="EUR">EUR</option>
                <option value="BGN">BGN</option>
              </select>
            </Field>
            <Field label={t("fields.conversionRate")}>
              <input
                type="number"
                step="0.0001"
                min="0"
                value={form.currency_conversion_rate ?? ""}
                onChange={(event) =>
                  setField(
                    "currency_conversion_rate",
                    event.target.value ? Number(event.target.value) : null,
                  )
                }
                className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              />
            </Field>
            <Toggle
              label={t("fields.declaredValue")}
              checked={form.declared_value_enabled}
              onChange={(value) => setField("declared_value_enabled", value)}
            />
          </div>
        </section>

        <section className="rounded-brand border border-champagne-beige bg-cream p-6">
          <h2 className="mb-4 text-sm font-semibold uppercase text-soft-brown">
            {t("sections.toggles")}
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Toggle label={t("fields.officeLocator")} checked={form.office_locator_enabled} onChange={(value) => setField("office_locator_enabled", value)} />
          </div>
        </section>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving || !isDirty}
            className="rounded-brand bg-charcoal px-5 py-2.5 text-sm font-medium text-warm-ivory transition-colors hover:bg-soft-brown disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSaving ? t("saving") : t("save")}
          </button>
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={isTesting}
            className="rounded-brand border border-champagne-beige bg-cream px-5 py-2.5 text-sm font-medium text-charcoal transition-colors hover:bg-champagne-beige/40 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isTesting ? t("testing") : t("testConnection")}
          </button>
          {testResult && (
            <span className={cn("rounded-brand border px-3 py-2 text-sm", statusClass)}>
              {t(`connectionStatus.${testResult.status}`)}: {testResult.message}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-soft-brown">{label}</span>
      {children}
    </label>
  );
}

function TextInput({ label, value, onChange }: { label: string; value: string | null; onChange: (value: string) => void }) {
  return (
    <Field label={label}>
      <input
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
      />
    </Field>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3 text-sm">
      <span className="font-medium text-charcoal">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-muted-gold"
      />
    </label>
  );
}

function CredentialState({ label, value }: { label: string; value: boolean }) {
  const t = useTranslations("admin.econt");
  return (
    <div>
      <dt className="text-soft-brown">{label}</dt>
      <dd className={value ? "font-medium text-green-700" : "font-medium text-amber-700"}>
        {value ? t("configured") : t("missing")}
      </dd>
    </div>
  );
}
