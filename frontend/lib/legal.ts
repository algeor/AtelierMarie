import type { Locale } from "@/i18n/routing";

export const LEGAL_IDENTITY = {
  tradingName: "Atelier Marie",
  legalName: "TODO: legal entity name",
  country: "Bulgaria",
  geographicAddress: "TODO: geographic business address",
  contactEmail: "contacts@theateliermarie.com",
  registrationNumber: "TODO: registration number",
  vatNumber: "TODO: VAT number or not VAT registered",
  responsiblePartyName: "Atelier Marie",
  responsiblePartyAddress: "TODO: geographic business address",
  responsiblePartyEmail: "contacts@theateliermarie.com",
} as const;

export const LEGAL_REVIEW_REQUIRED = [
  "legalName",
  "geographicAddress",
  "registrationNumber",
  "vatNumber",
  "responsiblePartyAddress",
] as const;

export type PolicyKey = "terms" | "privacy" | "cookies" | "contact";

export function policyPath(policy: PolicyKey) {
  return `/${policy}` as const;
}

export function localizedPolicyPath(locale: Locale, policy: PolicyKey) {
  return `/${locale}${policyPath(policy)}`;
}
