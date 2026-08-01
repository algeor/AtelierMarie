"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { createSellerLegalProfile, getAccountingConfig } from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";

type LegalForm = {
  company_display_name: string;
  legal_name: string;
  uic_eik: string;
  vat_identification_number: string;
  registered_address_line1: string;
  registered_address_line2: string;
  registered_address_city: string;
  registered_address_postal_code: string;
  registered_address_country: string;
  contact_email: string;
  default_currency: string;
  reviewed: boolean;
};

const EMPTY_FORM: LegalForm = {
  company_display_name: "",
  legal_name: "",
  uic_eik: "",
  vat_identification_number: "",
  registered_address_line1: "",
  registered_address_line2: "",
  registered_address_city: "",
  registered_address_postal_code: "",
  registered_address_country: "Bulgaria",
  contact_email: "",
  default_currency: "EUR",
  reviewed: false,
};

function todayDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

function addressString(address: Record<string, unknown> | null | undefined, key: string): string {
  const value = address?.[key];
  return typeof value === "string" ? value : "";
}

function buildRegisteredAddress(form: LegalForm): Record<string, string> | null {
  const address = {
    line1: form.registered_address_line1.trim(),
    line2: form.registered_address_line2.trim(),
    city: form.registered_address_city.trim(),
    postal_code: form.registered_address_postal_code.trim(),
    country: form.registered_address_country.trim(),
  };
  const entries = Object.entries(address).filter(([, value]) => value);
  return entries.length > 0 ? Object.fromEntries(entries) : null;
}

function formatAddress(form: LegalForm): string {
  const cityLine = [form.registered_address_postal_code, form.registered_address_city]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
  return [
    form.registered_address_line1,
    form.registered_address_line2,
    cityLine,
    form.registered_address_country,
  ]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(", ");
}

export default function AdminLegalPage() {
  const t = useTranslations("admin.legal");
  const common = useTranslations("common");
  const [form, setForm] = useState<LegalForm>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getAccountingConfig()
      .then((config) => {
        if (cancelled) return;
        const profile = config.seller_profile;
        if (!profile) return;
        const address = profile.registered_address;
        setForm({
          company_display_name: profile.company_display_name ?? "",
          legal_name: profile.legal_name ?? "",
          uic_eik: profile.uic_eik ?? "",
          vat_identification_number: profile.vat_identification_number ?? "",
          registered_address_line1: addressString(address, "line1") || addressString(address, "formatted"),
          registered_address_line2: addressString(address, "line2"),
          registered_address_city: addressString(address, "city"),
          registered_address_postal_code: addressString(address, "postal_code"),
          registered_address_country: addressString(address, "country") || "Bulgaria",
          contact_email: profile.contact_email ?? "",
          default_currency: profile.default_currency,
          reviewed: profile.reviewed,
        });
      })
      .catch(() => {
        if (!cancelled) setError(t("loadError"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [t]);

  const preview = useMemo(() => {
    const address = formatAddress(form) || "TODO: geographic business address";
    return {
      tradingName: form.company_display_name.trim() || "Atelier Marie",
      legalName: form.legal_name.trim() || "TODO: legal entity name",
      address,
      country: form.registered_address_country.trim() || "Bulgaria",
      contactEmail: form.contact_email.trim() || "contacts@theateliermarie.com",
      registrationNumber: form.uic_eik.trim() || "TODO: registration number",
      vatNumber: form.vat_identification_number.trim() || "TODO: VAT number or not VAT registered",
    };
  }, [form]);

  function updateField(field: keyof LegalForm, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    setSaving(true);
    setError(null);
    setSaveNotice(false);
    try {
      await createSellerLegalProfile({
        effective_date: todayDate(),
        reviewed: form.reviewed,
        company_display_name: emptyToNull(form.company_display_name),
        legal_name: emptyToNull(form.legal_name),
        uic_eik: emptyToNull(form.uic_eik),
        vat_identification_number: emptyToNull(form.vat_identification_number),
        registered_address: buildRegisteredAddress(form),
        contact_email: emptyToNull(form.contact_email),
        bank_details: null,
        default_currency: form.default_currency.trim().toUpperCase() || "EUR",
      });
      setSaveNotice(true);
    } catch {
      setError(t("saveError"));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-soft-brown">{t("loading")}</p>;
  }

  return (
    <div className="space-y-6">
      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation message={common("saved")} onDismiss={() => setSaveNotice(false)} />}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-soft-brown">{t("subtitle")}</p>
        </div>
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {saving ? t("saving") : common("save")}
        </button>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-brand border border-champagne-beige bg-cream p-5">
          <h2 className="font-heading text-xl text-charcoal">{t("formTitle")}</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <TextField label={t("companyDisplayName")} value={form.company_display_name} onChange={(value) => updateField("company_display_name", value)} placeholder="Atelier Marie" />
            <TextField label={t("legalName")} value={form.legal_name} onChange={(value) => updateField("legal_name", value)} />
            <TextField label={t("uicEik")} value={form.uic_eik} onChange={(value) => updateField("uic_eik", value)} />
            <TextField label={t("vatIdentificationNumber")} value={form.vat_identification_number} onChange={(value) => updateField("vat_identification_number", value)} />
            <TextField label={t("addressLine1")} value={form.registered_address_line1} onChange={(value) => updateField("registered_address_line1", value)} className="md:col-span-2" />
            <TextField label={t("addressLine2")} value={form.registered_address_line2} onChange={(value) => updateField("registered_address_line2", value)} className="md:col-span-2" />
            <TextField label={t("city")} value={form.registered_address_city} onChange={(value) => updateField("registered_address_city", value)} />
            <TextField label={t("postalCode")} value={form.registered_address_postal_code} onChange={(value) => updateField("registered_address_postal_code", value)} />
            <TextField label={t("country")} value={form.registered_address_country} onChange={(value) => updateField("registered_address_country", value)} />
            <TextField label={t("contactEmail")} type="email" value={form.contact_email} onChange={(value) => updateField("contact_email", value)} placeholder="contacts@theateliermarie.com" />
            <TextField label={t("currency")} value={form.default_currency} onChange={(value) => updateField("default_currency", value.toUpperCase())} />
            <label className="flex items-center gap-2 self-end text-sm text-soft-brown">
              <input type="checkbox" checked={form.reviewed} onChange={(event) => updateField("reviewed", event.target.checked)} />
              {t("reviewed")}
            </label>
          </div>
        </section>

        <section className="rounded-brand border border-champagne-beige bg-cream p-5 xl:sticky xl:top-24 xl:self-start">
          <h2 className="font-heading text-xl text-charcoal">{t("previewTitle")}</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <PreviewRow label={t("companyDisplayName")} value={preview.tradingName} />
            <PreviewRow label={t("legalName")} value={preview.legalName} />
            <PreviewRow label={t("address")} value={preview.address} />
            <PreviewRow label={t("country")} value={preview.country} />
            <PreviewRow label={t("contactEmail")} value={preview.contactEmail} />
            <PreviewRow label={t("uicEik")} value={preview.registrationNumber} />
            <PreviewRow label={t("vatIdentificationNumber")} value={preview.vatNumber} />
          </dl>
        </section>
      </div>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  className = "",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  className?: string;
}) {
  return (
    <label className={`text-sm text-soft-brown ${className}`}>
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm text-charcoal"
        placeholder={placeholder ?? label}
      />
    </label>
  );
}

function PreviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-medium text-charcoal">{label}</dt>
      <dd className="mt-0.5 break-words text-soft-brown">{value}</dd>
    </div>
  );
}
