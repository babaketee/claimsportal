import type { Role } from "./types";

// ---------------------------------------------------------------------------
// Demo accounts — swap for real auth (IMS REST API / Okta / Azure AD SSO /
// OTP via Africa's Talking or Twilio) before going to production.
// ---------------------------------------------------------------------------

export interface DemoAccount {
  password: string;
  role: Role;
  full_name: string;
}

export const DEMO_ACCOUNTS: Record<string, DemoAccount> = {
  "client@insure.demo": { password: "Assured#99", role: "client", full_name: "Kamau Mwangi" },
  "officer@insure.demo": {
    password: "Handler#99",
    role: "claims_officer",
    full_name: "Njeri Kariuki",
  },
  "hoc@insure.demo": {
    password: "Oversee#99",
    role: "head_of_claims",
    full_name: "David Otieno",
  },
  "assessor@insure.demo": {
    password: "Survey#99",
    role: "assessor",
    full_name: "Apollo Surveyors — J. Kamau",
  },
  "garage@insure.demo": {
    password: "Wrench#99",
    role: "garage",
    full_name: "Kiambu Auto Works Ltd",
  },
  "investigator@insure.demo": {
    password: "Sleuth#99",
    role: "investigator",
    full_name: "Eastleigh Detective Agency",
  },
  "finance@insure.demo": {
    password: "Invoice#99",
    role: "finance",
    full_name: "Susan Wambui",
  },
  "cfo@insure.demo": {
    password: "Reserves#99",
    role: "finance_head",
    full_name: "Michael Kiptoo",
  },
  "spares@insure.demo": {
    password: "Catalog#99",
    role: "spare_parts",
    full_name: "AutoSpares Kenya Ltd",
  },
  "legal@insure.demo": {
    password: "Counsel#99",
    role: "legal",
    full_name: "Faith Achieng, Legal Counsel",
  },
  "admin@insure.demo": {
    password: "SysCtrl#99",
    role: "admin",
    full_name: "IT & Operations Admin",
  },
  "super@insure.demo": {
    password: "Super#99",
    role: "super_admin",
    full_name: "System Administrator",
  },
};
