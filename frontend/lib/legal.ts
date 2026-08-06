import type { Locale } from "@/i18n/routing";
import { getLegalIdentity } from "@/lib/api";
import type { LegalIdentityResponse } from "@/lib/types";

export interface LegalIdentity {
  tradingName: string;
  legalName: string | null;
  country: string;
  geographicAddress: string | null;
  contactEmail: string;
  registrationNumber: string | null;
  vatNumber: string | null;
  responsiblePartyName: string;
  responsiblePartyAddress: string | null;
  responsiblePartyEmail: string;
}

export const LEGAL_IDENTITY: LegalIdentity = {
  tradingName: "Atelier Marie",
  legalName: null,
  country: "Bulgaria",
  geographicAddress: null,
  contactEmail: "contacts@theateliermarie.com",
  registrationNumber: null,
  vatNumber: null,
  responsiblePartyName: "Atelier Marie",
  responsiblePartyAddress: null,
  responsiblePartyEmail: "contacts@theateliermarie.com",
};

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

export function hasLegalIdentityValue(
  value: string | null | undefined,
): value is string {
  return Boolean(value?.trim());
}

function mapLegalIdentity(identity: LegalIdentityResponse): LegalIdentity {
  return {
    tradingName: identity.trading_name,
    legalName: identity.legal_name,
    country: identity.country,
    geographicAddress: identity.geographic_address,
    contactEmail: identity.contact_email,
    registrationNumber: identity.registration_number,
    vatNumber: identity.vat_number,
    responsiblePartyName: identity.responsible_party_name,
    responsiblePartyAddress: identity.responsible_party_address,
    responsiblePartyEmail: identity.responsible_party_email,
  };
}

export async function loadLegalIdentity(): Promise<LegalIdentity> {
  try {
    return mapLegalIdentity(await getLegalIdentity());
  } catch {
    return LEGAL_IDENTITY;
  }
}
