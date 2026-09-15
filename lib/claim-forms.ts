import type { ClaimFormKey } from "./types";

// ---------------------------------------------------------------------------
// Structured definitions of the 7 real Definite Assurance claim forms
// supplied by the client, used to:
//   1. render the client-facing claim-submission form (Stage 3/4) with the
//      real fields from the paper form, per claim type;
//   2. drive the DocuSeal "claim_form" e-signature workflow (the form's own
//      declaration + DPA 2019 consent + signature block become the DocuSeal
//      document when a real template is configured, or a native fallback
//      form in demo mode);
//   3. supply the "mandatory / conditional documents" checklist referenced
//      in Appendix C of the workflow design, used to gate submission and to
//      feed the fraud-screening engine (missing-mandatory-document signal).
// ---------------------------------------------------------------------------

export interface ClaimFormField {
  name: string;
  label: string;
  type: "text" | "date" | "textarea" | "select" | "number";
  options?: string[];
  required?: boolean;
}

export interface ClaimFormSection {
  title: string;
  fields: ClaimFormField[];
}

export interface ClaimFormDefinition {
  key: ClaimFormKey;
  title: string;
  sourceDocument: string;
  description: string;
  sections: ClaimFormSection[];
  mandatoryDocuments: string[];
  conditionalDocuments: string[];
}

const consentSection: ClaimFormSection = {
  title: "Data Protection Act, 2019 — Privacy Notice & Consent",
  fields: [
    {
      name: "consent_processing",
      label:
        "I/We have read and understood the Privacy Notice and consent to Definite Assurance collecting, using, storing and processing my/our personal data (including sensitive data such as health information, where applicable) for underwriting, claims and settlement purposes.",
      type: "select",
      options: ["Agree"],
      required: true,
    },
    {
      name: "consent_sharing",
      label:
        "I/We consent to my/our personal data being shared with, and obtained from, reinsurers, other insurers, industry databases (IMIS/DMVIC), the IRA, AKI, intermediaries, assessors, investigators and service providers for underwriting, claims and fraud-prevention purposes.",
      type: "select",
      options: ["Agree"],
      required: true,
    },
    {
      name: "consent_contact",
      label:
        "I/We consent to Definite Assurance contacting me/us about this and related products and services by email, SMS, telephone and post.",
      type: "select",
      options: ["Agree", "Decline"],
      required: true,
    },
  ],
};

export const FORM_DEFINITIONS: Record<ClaimFormKey, ClaimFormDefinition> = {
  motor_accident: {
    key: "motor_accident",
    title: "Motor Accident Claim Form",
    sourceDocument: "MOTOR ACCIDENT CLAIM FORM — redesigned",
    description:
      "For motor own-damage, theft, fire, flood and third-party accident claims. No liability is admitted by the issue of this form.",
    sections: [
      {
        title: "Insured / Vehicle Details",
        fields: [
          { name: "insured_name", label: "Full Name of Insured", type: "text", required: true },
          { name: "insured_phone", label: "Telephone No. & Email", type: "text", required: true },
          { name: "vehicle_make_model", label: "Make & Model", type: "text", required: true },
          { name: "vehicle_reg", label: "Registration No.", type: "text", required: true },
          { name: "year_of_manufacture", label: "Year of Manufacture", type: "text" },
          { name: "purpose_of_use", label: "Purpose of Use", type: "text" },
        ],
      },
      {
        title: "Driver Information",
        fields: [
          { name: "driver_name", label: "Full Name of Driver", type: "text", required: true },
          { name: "driver_employee", label: "Your Employee?", type: "select", options: ["Yes", "No"] },
          { name: "driving_experience", label: "Driving Experience (years)", type: "text" },
        ],
      },
      {
        title: "Accident Particulars",
        fields: [
          { name: "accident_datetime", label: "Date & Time of Accident", type: "date", required: true },
          { name: "accident_location", label: "Precise Location", type: "text", required: true },
          { name: "weather", label: "Weather Conditions", type: "text" },
          { name: "fault", label: "Fault (Yes/No)", type: "select", options: ["Yes", "No", "Disputed"] },
          { name: "police_station", label: "Police Station", type: "text" },
          { name: "ob_number", label: "Constable / OB No.", type: "text" },
        ],
      },
      {
        title: "Damage & Third Parties",
        fields: [
          { name: "damage_description", label: "Brief Account of Damage", type: "textarea", required: true },
          { name: "third_party_details", label: "Third Party Owner / Reg No. / Insurer", type: "textarea" },
          { name: "persons_injured", label: "Persons Injured (name, relation, injuries)", type: "textarea" },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: [
      "Claim form",
      "Driving licence",
      "Log book copy",
      "Police abstract",
      "Photographs of the damage",
      "Repair estimate",
    ],
    conditionalDocuments: [
      "Financier consent (where the vehicle is financed)",
      "Interpreter's statement (where applicable)",
      "Third party's demand letter, repair estimate & insured driver's statement (third-party property)",
      "Medical report, treatment records, demand letter from advocates (third-party bodily injury)",
      "Death certificate and letters of administration (fatal claims)",
    ],
  },
  windscreen: {
    key: "windscreen",
    title: "Windscreen / Glass Claim Form",
    sourceDocument: "WINDSCREEN CLAIM FORM",
    description: "For windscreen, rear screen, door glass or sunroof damage claims.",
    sections: [
      {
        title: "Vehicle & Damage Details",
        fields: [
          { name: "vehicle_reg", label: "Vehicle Registration No.", type: "text", required: true },
          { name: "make_model", label: "Make & Model", type: "text" },
          { name: "date_of_damage", label: "Date of Damage", type: "date", required: true },
          { name: "location", label: "Location where damage occurred", type: "text", required: true },
          {
            name: "glass_damaged",
            label: "Glass damaged",
            type: "select",
            options: ["Windscreen", "Rear screen", "Door glass", "Sunroof"],
            required: true,
          },
          {
            name: "cause",
            label: "Cause",
            type: "select",
            options: ["Stone / flying object", "Accident", "Attempted theft", "Other"],
          },
          { name: "police_ob", label: "Police OB No. (if reported)", type: "text" },
          { name: "description", label: "Brief description of how the damage occurred", type: "textarea" },
        ],
      },
      {
        title: "Repair / Replacement",
        fields: [
          { name: "repairer_name", label: "Repairer / Fitter Name", type: "text" },
          { name: "quotation_amount", label: "Quotation Amount (KES)", type: "number" },
          { name: "policy_excess", label: "Policy Excess (KES)", type: "number" },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: ["Claim form", "Damaged-glass quotation / invoice"],
    conditionalDocuments: ["Police abstract (where reported to police)"],
  },
  all_risks: {
    key: "all_risks",
    title: "All Risks Claim Form",
    sourceDocument: "ALL RISKS CLAIM FORM — Claim for Property Damage or Loss",
    description: "For property damage or loss under an All Risks / fire / burglary section.",
    sections: [
      {
        title: "Policyholder & Circumstances of Loss",
        fields: [
          { name: "insured_name", label: "Full Name of Insured", type: "text", required: true },
          { name: "business_occupation", label: "Business or Occupation", type: "text" },
          { name: "date_of_loss", label: "Date of Loss", type: "date", required: true },
          { name: "place_of_loss", label: "Where loss occurred", type: "text", required: true },
          { name: "description", label: "Describe fully how the loss occurred", type: "textarea", required: true },
        ],
      },
      {
        title: "Theft / Malicious Damage",
        fields: [
          { name: "police_notified", label: "When were Police notified?", type: "date" },
          { name: "police_station", label: "Police Station / OB No.", type: "text" },
          { name: "method_of_entry", label: "Method of entry", type: "textarea" },
          { name: "alarm_fitted", label: "Alarm fitted? Functional?", type: "select", options: ["Yes", "No", "N/A"] },
        ],
      },
      {
        title: "Amount Claimed",
        fields: [
          { name: "total_amount_claimed", label: "Total Amount Claimed (KES)", type: "number", required: true },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: [
      "Claim form",
      "Proof of ownership",
      "Fire brigade or police report",
      "Photographs",
      "Schedule of loss",
      "Purchase invoices",
    ],
    conditionalDocuments: ["Structural engineer's report (building damage)"],
  },
  baggage_property: {
    key: "baggage_property",
    title: "Personal Baggage / Property Loss Claim Form",
    sourceDocument: "PERSONAL BAGGAGE / PROPERTY LOSS CLAIM FORM",
    description: "For personal baggage, goods-in-transit and personal property loss claims.",
    sections: [
      {
        title: "Policy & Insured Details",
        fields: [
          { name: "insured_name", label: "Full Name of Insured", type: "text", required: true },
          { name: "occupation", label: "Nature of Business / Occupation", type: "text" },
        ],
      },
      {
        title: "Circumstances of Loss",
        fields: [
          { name: "date_of_loss", label: "Date and Time of Loss", type: "date", required: true },
          { name: "place_of_loss", label: "Place of Occurrence", type: "text", required: true },
          { name: "description", label: "Detailed description of how the loss or damage occurred", type: "textarea", required: true },
          { name: "transit_route", label: "Transit Route (From / To, if in transit)", type: "text" },
        ],
      },
      {
        title: "Amount Claimed",
        fields: [
          { name: "property_description", label: "Full description of property lost / damaged", type: "textarea", required: true },
          { name: "net_claimed", label: "Net Amount Claimed (KES)", type: "number", required: true },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: ["Claim form", "Purchase receipts / proof of ownership", "Schedule of items lost"],
    conditionalDocuments: ["Police abstract (theft/malicious damage)", "Carrier's report (loss in transit)"],
  },
  wiba: {
    key: "wiba",
    title: "Workmen's Compensation (WIBA) Claim Form",
    sourceDocument: "WORKMEN'S COMPENSATION (WIBA) CLAIM FORM",
    description: "Completed by the employer in case of injury to, or death of, an employee.",
    sections: [
      {
        title: "Employer & Employee",
        fields: [
          { name: "employer_name", label: "Employer's Name", type: "text", required: true },
          { name: "employee_name", label: "Employee's Name", type: "text", required: true },
          { name: "employee_id", label: "ID No. / Occupation", type: "text" },
          { name: "under_direct_employment", label: "Was the injured under your direct employment?", type: "select", options: ["Yes", "No"] },
        ],
      },
      {
        title: "The Accident",
        fields: [
          { name: "accident_datetime", label: "Date & Hour of Incident", type: "date", required: true },
          { name: "place_of_occurrence", label: "Exact Place of Occurrence", type: "text", required: true },
          { name: "cause", label: "Cause of the Accident", type: "textarea", required: true },
        ],
      },
      {
        title: "The Injury & Treatment",
        fields: [
          { name: "injury_fatal", label: "Was the Injury Fatal?", type: "select", options: ["Yes", "No"] },
          { name: "particulars_of_injury", label: "Particulars of Injury (as certified by doctor)", type: "textarea" },
          { name: "medical_facility", label: "Medical Facility Name", type: "text" },
        ],
      },
      {
        title: "Safety Compliance",
        fields: [
          { name: "ppe_provided", label: "Was PPE provided?", type: "select", options: ["Yes", "No"] },
          { name: "ppe_worn", label: "Was employee wearing PPE at the time?", type: "select", options: ["Yes", "No"] },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: [
      "WIBA claim form",
      "DOSHS notification / reference",
      "Medical report",
      "Employer's statement",
    ],
    conditionalDocuments: ["Death certificate and letters of administration (fatal claims)", "Dependants' details (fatal claims)"],
  },
  personal_accident: {
    key: "personal_accident",
    title: "Personal Accident Claim Form",
    sourceDocument: "PERSONAL ACCIDENT CLAIM FORM",
    description: "For bodily injury claims under a personal accident policy, including third-party bodily-harm motor claims.",
    sections: [
      {
        title: "Claimant & Circumstances",
        fields: [
          { name: "insured_name", label: "Full Name of Insured / Claimant", type: "text", required: true },
          { name: "occupation", label: "Occupation of Injured", type: "text" },
          { name: "incident_datetime", label: "Date / Time / Place", type: "date", required: true },
          { name: "how_it_happened", label: "How did the accident happen?", type: "textarea", required: true },
          { name: "nature_of_injuries", label: "Nature of Injuries", type: "textarea", required: true },
        ],
      },
      {
        title: "Medical",
        fields: [
          { name: "attending_doctor", label: "Attending Medical Doctor (Name/Address)", type: "text" },
          { name: "confinement_duration", label: "Confinement Duration (bed / house)", type: "text" },
          { name: "prior_medical_history", label: "Treatment in last 5 years", type: "textarea" },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: ["Claim form", "Medical certificate", "Medical report / discharge summary", "Itemised hospital bill"],
    conditionalDocuments: ["Police abstract (where the injury arose from an accident)", "Pre-authorisation (specialist referral)"],
  },
  investigator_notification: {
    key: "investigator_notification",
    title: "Notification of Incident Form (for Investigators)",
    sourceDocument: "NOTIFICATION OF INCIDENT FORM — (FOR INVESTIGATORS)",
    description:
      "Filed by the assigned investigator, not the client. Captures accident particulars and — critically — a fraud-risk & report log used directly by the fraud-screening engine.",
    sections: [
      {
        title: "Assignment",
        fields: [
          { name: "investigator_name", label: "Investigator Name & Firm", type: "text", required: true },
          { name: "mode_of_report", label: "Mode of Report", type: "select", options: ["Telephone", "Walk-in", "Media", "Mobile App"] },
        ],
      },
      {
        title: "Accident / Incident Particulars",
        fields: [
          { name: "accident_datetime", label: "Date & Time of Accident", type: "date", required: true },
          { name: "location", label: "Location of Accident", type: "text", required: true },
          { name: "police_station", label: "Police Station Reported", type: "text" },
          { name: "injured_count", label: "Number of Injured Persons", type: "number" },
          { name: "deceased_count", label: "Number of Deceased Persons", type: "number" },
        ],
      },
      {
        title: "Fraud-Risk & Report Log",
        fields: [
          { name: "fraud_suspected", label: "Suspected Fraud Indicators?", type: "select", options: ["No", "Yes"], required: true },
          { name: "fraud_basis", label: "Basis / Notes", type: "textarea" },
        ],
      },
    ],
    mandatoryDocuments: ["Investigator field report"],
    conditionalDocuments: ["Photographs of scene / vehicle", "Witness statements"],
  },
  general_claim: {
    key: "general_claim",
    title: "General Claim Declaration & Consent Form",
    sourceDocument: "Definite Assurance — standard claim declaration (no specific paper form supplied for this class)",
    description:
      "Used for classes not yet covered by a dedicated paper form (e.g. business interruption, public liability). Captures the standard declaration and DPA 2019 consent common to every Definite Assurance claim form.",
    sections: [
      {
        title: "Claim Declaration",
        fields: [
          { name: "insured_name", label: "Full Name of Insured", type: "text", required: true },
          { name: "date_of_loss", label: "Date of Loss", type: "date", required: true },
          { name: "description", label: "Description of loss / event", type: "textarea", required: true },
          { name: "amount_claimed", label: "Amount Claimed (KES)", type: "number", required: true },
        ],
      },
      consentSection,
    ],
    mandatoryDocuments: ["Claim form", "Proof of loss / invoices"],
    conditionalDocuments: ["Police / regulator report (where applicable)"],
  },
};

/** Maps the claim_type strings used elsewhere in the app to the closest paper form. */
export const FORM_KEY_BY_CLAIM_TYPE: Record<string, ClaimFormKey> = {
  "Motor Bumper": "motor_accident",
  "Own Damage — Collision": "motor_accident",
  "Theft": "motor_accident",
  "Third Party Property": "motor_accident",
  "Fire Damage": "motor_accident",
  "Flood Damage": "motor_accident",
  "Windscreen": "windscreen",
  "Third Party Bodily Harm": "personal_accident",
  "Business Fire": "all_risks",
  "Business Burglary": "all_risks",
  "Goods in Transit": "baggage_property",
  WIBA: "wiba",
  "Business Interruption": "general_claim",
  "Public Liability": "general_claim",
};

export function formKeyForClaimType(claim_type: string): ClaimFormKey {
  return FORM_KEY_BY_CLAIM_TYPE[claim_type] ?? "general_claim";
}

export function formDefinitionFor(claim_type: string): ClaimFormDefinition {
  return FORM_DEFINITIONS[formKeyForClaimType(claim_type)];
}
