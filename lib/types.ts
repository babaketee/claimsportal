// ---------------------------------------------------------------------------
// Domain types shared across the app (server + client components).
// ---------------------------------------------------------------------------

export type Role =
  | "client"
  | "claims_officer"
  | "head_of_claims"
  | "assessor"
  | "garage"
  | "investigator"
  | "finance"
  | "finance_head"
  | "spare_parts"
  | "legal"
  | "admin"
  | "super_admin";

export const ROLE_LABELS: Record<Role, string> = {
  client: "Policyholder / Client",
  claims_officer: "Claims Officer",
  head_of_claims: "Head of Claims",
  assessor: "Assessor",
  garage: "Garage / Repairer",
  investigator: "Investigator",
  finance: "Finance / Accounts Payable",
  finance_head: "Finance Head",
  spare_parts: "Spare Parts Provider",
  legal: "Legal Officer",
  admin: "Internal Staff / Admin",
  super_admin: "Super Admin",
};

export type ClaimCategory = "Motor" | "Business";

// ---------------------------------------------------------------------------
// Claim status model — aligned to the Stackwire "Proposed Claims Portal
// Workflow Design" (10-stage lifecycle, section 6 status table).
// ---------------------------------------------------------------------------

export type ClaimStatus =
  | "Draft"
  | "Submitted"
  | "Under triage"
  | "Under investigation and assessment"
  | "On hold - awaiting information"
  | "Pending approval"
  | "Approved"
  | "Repudiated"
  | "Under repair"
  | "Awaiting reinspection"
  | "Pending payment"
  | "Paid"
  | "Closed"
  | "Reopened"
  | "Withdrawn";

export const CLAIM_STATUSES: ClaimStatus[] = [
  "Draft",
  "Submitted",
  "Under triage",
  "Under investigation and assessment",
  "On hold - awaiting information",
  "Pending approval",
  "Approved",
  "Repudiated",
  "Under repair",
  "Awaiting reinspection",
  "Pending payment",
  "Paid",
  "Closed",
  "Reopened",
  "Withdrawn",
];

export const CLOSED_STATUSES: ClaimStatus[] = ["Paid", "Closed", "Repudiated", "Withdrawn"];

/** The 10-stage lifecycle from the design document, and which statuses sit in each. */
export const LIFECYCLE_STAGES: { stage: number; name: string; statuses: ClaimStatus[] }[] = [
  { stage: 1, name: "Login / Policy Pull", statuses: ["Draft"] },
  { stage: 2, name: "Policy Selection / Autofill", statuses: ["Draft"] },
  { stage: 3, name: "Claim Details / Evidence", statuses: ["Draft"] },
  { stage: 4, name: "Submission", statuses: ["Submitted"] },
  { stage: 5, name: "Fraud Screening and Triage", statuses: ["Under triage"] },
  {
    stage: 6,
    name: "Parallel Investigation + Assessment",
    statuses: ["Under investigation and assessment", "On hold - awaiting information"],
  },
  { stage: 7, name: "Core System Review / Human Approval", statuses: ["Pending approval"] },
  {
    stage: 8,
    name: "Repair / Parts / Reinspection",
    statuses: ["Approved", "Under repair", "Awaiting reinspection"],
  },
  { stage: 9, name: "Finance Disbursement", statuses: ["Pending payment"] },
  { stage: 10, name: "Closure", statuses: ["Paid", "Closed", "Repudiated", "Withdrawn", "Reopened"] },
];

export function stageForStatus(status: ClaimStatus): number {
  const found = LIFECYCLE_STAGES.find((s) => s.statuses.includes(status));
  return found ? found.stage : 1;
}

export function stageNameForStatus(status: ClaimStatus): string {
  const found = LIFECYCLE_STAGES.find((s) => s.statuses.includes(status));
  return found ? found.name : "Login / Policy Pull";
}

export type Urgency = "Low" | "Medium" | "High";

export interface Claim {
  claim_ref: string;
  category: ClaimCategory;
  claim_type: string;
  status: ClaimStatus;
  policy_number: string;
  insured_name: string;
  client_email: string | null;
  vehicle_reg: string | null;
  location: string;
  date_of_loss: string | null;
  date_reported: string;
  claim_amount: number;
  urgency: Urgency;
  description: string;
  assigned_officer: string | null;
  expert_type: "assessor" | "garage" | "investigator" | null;
  created_at: string;
}

export interface Reserve {
  reserve_id: string;
  claim_ref: string;
  reserve_type: "initial" | "supplemental";
  amount: number;
  purpose: string;
  created_by: string;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  status: "pending" | "approved" | "released";
  note: string;
}

export interface DiaryEntry {
  entry_id: string;
  claim_ref: string;
  task: string;
  due_date: string;
  assigned_to: string;
  priority: "low" | "normal" | "high" | "urgent";
  status: "open" | "done" | "overdue";
  created_by: string;
  created_at: string;
  completed_at: string | null;
  note: string;
}

export interface Communication {
  comm_id: string;
  claim_ref: string;
  channel: "sms" | "call" | "email" | "letter" | "whatsapp";
  direction: "inbound" | "outbound";
  contact_name: string;
  contact_phone: string;
  summary: string;
  outcome: string;
  consent_obtained: "yes" | "no";
  created_by: string;
  created_at: string;
}

export interface ExpertAssignment {
  assignment_id: string;
  claim_ref: string;
  expert_type: "assessor" | "garage" | "investigator" | "loss_adjuster";
  expert_name: string;
  expert_phone: string;
  expert_company: string;
  status: "pending" | "accepted" | "in_progress" | "completed" | "rejected";
  assigned_by: string;
  assigned_at: string;
  accepted_at: string | null;
  completed_at: string | null;
  estimated_cost: number;
  actual_cost: number | null;
  note: string;
}

export type DocType =
  | "police_abstract"
  | "medical_report"
  | "invoice"
  | "surveyor_report"
  | "demand_letter"
  | "id_document"
  | "photo"
  | "discharge_voucher"
  | "engagement_letter"
  | "consent_form"
  | "other";

export type OcrStatus = "pending" | "done" | "unsupported" | "failed";

export interface ClaimDocument {
  doc_id: string;
  claim_ref: string;
  doc_type: DocType;
  filename: string;
  file_size: number;
  mime_type: string;
  file_path: string | null;
  uploaded_by: string;
  uploaded_at: string;
  version: number;
  note: string;
  ocr_status: OcrStatus;
  ocr_text: string | null;
  exif_json: string | null;
}

/** Parsed shape of ClaimDocument.exif_json when present. */
export interface PhotoMetadata {
  captured_at: string | null;
  gps_lat: number | null;
  gps_lng: number | null;
  camera_make: string | null;
  camera_model: string | null;
  has_gps: boolean;
  days_from_loss: number | null;
  flags: string[];
}

export interface Settlement {
  settlement_id: string;
  claim_ref: string;
  settlement_type: "officer_recommend" | "hoc_approval" | "finance_payment";
  amount: number;
  payee_name: string;
  payee_type: "assessor" | "garage" | "investigator" | "spare_parts" | "third_party" | "insured";
  wht_rate: number;
  wht_amount: number;
  net_amount: number;
  status: "pending" | "approved" | "rejected" | "paid" | "cancelled";
  recommended_by: string | null;
  recommended_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
  paid_at: string | null;
  bank_ref: string | null;
  note: string;
}

export type DocusealWorkflow =
  | "settlement_discharge"
  | "demand_letter"
  | "claim_form"
  | "engagement_letter";

export const DOCUSEAL_WORKFLOW_LABELS: Record<DocusealWorkflow, string> = {
  settlement_discharge: "Settlement Discharge Voucher",
  demand_letter: "Demand Letter / Repudiation Notice",
  claim_form: "Claim Form, Declaration & DPA Consent",
  engagement_letter: "Service Provider Engagement Letter",
};

/** Which of the 7 uploaded claim-form templates a submission uses (claim_form workflow only). */
export type ClaimFormKey =
  | "motor_accident"
  | "windscreen"
  | "all_risks"
  | "baggage_property"
  | "wiba"
  | "personal_accident"
  | "investigator_notification"
  | "general_claim";

export interface DocusealSubmission {
  submission_id: string;
  claim_ref: string;
  workflow: DocusealWorkflow;
  form_key: ClaimFormKey | null;
  template_id: string | null;
  docuseal_submission_id: string | null;
  signer_name: string;
  signer_email: string;
  status: "not_configured" | "pending" | "completed" | "declined" | "expired";
  embed_src: string | null;
  created_by: string;
  created_at: string;
  completed_at: string | null;
}

// ---------------------------------------------------------------------------
// Audit trail — immutable claim status history (design principle: "evidence,
// not memory").
// ---------------------------------------------------------------------------

export interface ClaimStatusHistoryEntry {
  history_id: string;
  claim_ref: string;
  from_status: string | null;
  to_status: string;
  changed_by: string;
  changed_at: string;
  note: string;
}

// ---------------------------------------------------------------------------
// AI-assisted fraud screening & triage (Stage 5). Scores and routes only;
// never auto-approves or auto-declines — a human always makes the call.
// ---------------------------------------------------------------------------

export type FraudRiskBand = "Low" | "Medium" | "High";

export interface FraudIndicator {
  code: string;
  label: string;
  weight: number;
  detail: string;
}

export interface FraudAssessment {
  assessment_id: string;
  claim_ref: string;
  score: number;
  risk_band: FraudRiskBand;
  indicators_json: string; // JSON.stringify(FraudIndicator[])
  recommended_action: string;
  computed_at: string;
  computed_by: string; // 'system' for the automated engine
  review_status: "pending_review" | "reviewed";
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_decision: "proceed" | "escalate_to_investigator" | "cleared" | null;
  review_note: string;
}

// ---------------------------------------------------------------------------
// Configuration engine — versioned, effective-dated, maker-checker approved
// settings (fraud thresholds, TAT/SLA targets, approval limits, document
// checklists). Section 10 of the design document.
// ---------------------------------------------------------------------------

export type ConfigStatus = "approved" | "pending_approval";

export interface ConfigItem {
  config_key: string;
  version: number;
  value_json: string;
  status: ConfigStatus;
  proposed_by: string;
  proposed_at: string;
  approved_by: string | null;
  approved_at: string | null;
  effective_date: string;
  note: string;
}

export interface Rfq {
  rfq_ref: string;
  claim_ref: string;
  part_description: string;
  quantity: number;
  status: "open" | "awarded" | "cancelled";
  created_by: string;
  created_at: string;
}

export interface InvestigatorReport {
  report_id: string;
  claim_ref: string;
  investigator_name: string;
  mode_of_report: string;
  accident_datetime: string;
  location: string;
  police_station: string;
  injured_count: number;
  deceased_count: number;
  fraud_suspected: "yes" | "no";
  fraud_basis: string;
  created_by: string;
  created_at: string;
}

export interface Bid {
  bid_ref: string;
  rfq_ref: string;
  provider: string;
  brand: string;
  condition: string;
  unit_price: number;
  lead_days: number;
  warranty: string;
  rating: number;
  submitted_at: string;
  status: "submitted" | "won" | "lost";
}
