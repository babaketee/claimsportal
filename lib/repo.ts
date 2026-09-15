import { getDb } from "./db";
import type {
  Bid,
  Claim,
  ClaimDocument,
  ClaimFormKey,
  ClaimStatusHistoryEntry,
  Communication,
  ConfigItem,
  DiaryEntry,
  DocType,
  DocusealSubmission,
  DocusealWorkflow,
  ExpertAssignment,
  FraudAssessment,
  FraudRiskBand,
  InvestigatorReport,
  OcrStatus,
  Reserve,
  Rfq,
  Settlement,
} from "./types";

function id(prefix: string): string {
  const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const rand = Math.random().toString(16).slice(2, 8).toUpperCase();
  return `${prefix}-${stamp}-${rand}`;
}

const now = () => new Date().toISOString();

// ---------------------------------------------------------------------------
// Claims
// ---------------------------------------------------------------------------

export function createClaim(claim: Omit<Claim, "created_at">): void {
  getDb()
    .prepare(
      `INSERT INTO claims (claim_ref, category, claim_type, status, policy_number, insured_name, client_email, vehicle_reg, location, date_of_loss, date_reported, claim_amount, urgency, description, assigned_officer, expert_type, created_at)
       VALUES (@claim_ref, @category, @claim_type, @status, @policy_number, @insured_name, @client_email, @vehicle_reg, @location, @date_of_loss, @date_reported, @claim_amount, @urgency, @description, @assigned_officer, @expert_type, @created_at)`
    )
    .run({ ...claim, created_at: now() });
}

export function avgAmountForType(claim_type: string, excludeClaimRef?: string): number {
  const row = getDb()
    .prepare(
      "SELECT COALESCE(AVG(claim_amount),0) a FROM claims WHERE claim_type=? AND claim_ref<>?"
    )
    .get(claim_type, excludeClaimRef ?? "__none__") as { a: number };
  return row.a;
}

export function updateClaimStatus(
  claim_ref: string,
  status: string,
  changed_by = "system",
  note = ""
): void {
  const db = getDb();
  const prior = getClaim(claim_ref);
  const tx = db.transaction(() => {
    db.prepare("UPDATE claims SET status=? WHERE claim_ref=?").run(status, claim_ref);
    db.prepare(
      `INSERT INTO claim_status_history (history_id, claim_ref, from_status, to_status, changed_by, changed_at, note)
       VALUES (@history_id, @claim_ref, @from_status, @to_status, @changed_by, @changed_at, @note)`
    ).run({
      history_id: id("HST"),
      claim_ref,
      from_status: prior?.status ?? null,
      to_status: status,
      changed_by,
      changed_at: now(),
      note,
    });
  });
  tx();
}

export function getStatusHistory(claim_ref: string): ClaimStatusHistoryEntry[] {
  return getDb()
    .prepare("SELECT * FROM claim_status_history WHERE claim_ref=? ORDER BY changed_at ASC")
    .all(claim_ref) as ClaimStatusHistoryEntry[];
}

/** Claims from the same client (by email) or policy number, for fraud frequency checks. */
export function getClaimsForClientOrPolicy(
  client_email: string | null,
  policy_number: string,
  excludeClaimRef?: string
): Claim[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT * FROM claims WHERE (policy_number = @policy_number OR (client_email IS NOT NULL AND client_email = @client_email)) AND claim_ref <> @exclude`
    )
    .all({
      policy_number,
      client_email: client_email ?? "__none__",
      exclude: excludeClaimRef ?? "__none__",
    }) as Claim[];
  return rows;
}

/** Other claims against the same vehicle registration, for duplicate-loss detection. */
export function getClaimsForVehicle(vehicle_reg: string, excludeClaimRef?: string): Claim[] {
  if (!vehicle_reg) return [];
  return getDb()
    .prepare("SELECT * FROM claims WHERE vehicle_reg = ? AND claim_ref <> ?")
    .all(vehicle_reg, excludeClaimRef ?? "__none__") as Claim[];
}

export function getClaim(claim_ref: string): Claim | undefined {
  return getDb().prepare("SELECT * FROM claims WHERE claim_ref = ?").get(claim_ref) as
    | Claim
    | undefined;
}

export function listClaims(filters: {
  status?: string;
  category?: string;
  client_email?: string;
  assigned_officer?: string;
  expert_type?: string;
  q?: string;
  limit?: number;
} = {}): Claim[] {
  const clauses: string[] = [];
  const params: Record<string, unknown> = {};
  if (filters.status && filters.status !== "All") {
    clauses.push("status = @status");
    params.status = filters.status;
  }
  if (filters.category && filters.category !== "All") {
    clauses.push("category = @category");
    params.category = filters.category;
  }
  if (filters.client_email) {
    clauses.push("client_email = @client_email");
    params.client_email = filters.client_email;
  }
  if (filters.assigned_officer) {
    clauses.push("assigned_officer = @assigned_officer");
    params.assigned_officer = filters.assigned_officer;
  }
  if (filters.expert_type) {
    clauses.push("expert_type = @expert_type");
    params.expert_type = filters.expert_type;
  }
  if (filters.q) {
    clauses.push(
      "(claim_ref LIKE @q OR insured_name LIKE @q OR vehicle_reg LIKE @q OR policy_number LIKE @q)"
    );
    params.q = `%${filters.q}%`;
  }
  const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
  const limit = filters.limit ? `LIMIT ${filters.limit}` : "";
  return getDb()
    .prepare(`SELECT * FROM claims ${where} ORDER BY date_reported DESC ${limit}`)
    .all(params) as Claim[];
}

export function countClaimsByStatus(): { status: string; n: number }[] {
  return getDb()
    .prepare("SELECT status, COUNT(*) as n FROM claims GROUP BY status")
    .all() as { status: string; n: number }[];
}

export function countClaimsByType(): { claim_type: string; n: number; total: number }[] {
  return getDb()
    .prepare(
      "SELECT claim_type, COUNT(*) as n, COALESCE(SUM(claim_amount),0) as total FROM claims GROUP BY claim_type ORDER BY n DESC"
    )
    .all() as { claim_type: string; n: number; total: number }[];
}

export function claimsSummary(): {
  total: number;
  open: number;
  settled: number;
  totalExposure: number;
  settledValue: number;
} {
  const db = getDb();
  const total = (db.prepare("SELECT COUNT(*) n FROM claims").get() as { n: number }).n;
  const open = (
    db
      .prepare(
        "SELECT COUNT(*) n FROM claims WHERE status NOT IN ('Paid','Closed','Repudiated','Withdrawn')"
      )
      .get() as { n: number }
  ).n;
  const settled = (
    db.prepare("SELECT COUNT(*) n FROM claims WHERE status IN ('Paid','Closed')").get() as { n: number }
  ).n;
  const totalExposure = (
    db
      .prepare(
        "SELECT COALESCE(SUM(claim_amount),0) t FROM claims WHERE status NOT IN ('Repudiated','Withdrawn')"
      )
      .get() as { t: number }
  ).t;
  const settledValue = (
    db.prepare("SELECT COALESCE(SUM(claim_amount),0) t FROM claims WHERE status IN ('Paid','Closed')").get() as {
      t: number;
    }
  ).t;
  return { total, open, settled, totalExposure, settledValue };
}

// ---------------------------------------------------------------------------
// Reserves
// ---------------------------------------------------------------------------

export function setReserve(input: {
  claim_ref: string;
  reserve_type: "initial" | "supplemental";
  amount: number;
  purpose: string;
  created_by: string;
  note?: string;
}): string | null {
  if (!input.claim_ref || input.amount <= 0) return null;
  const reserve_id = id("RSV");
  getDb()
    .prepare(
      `INSERT INTO reserves (reserve_id, claim_ref, reserve_type, amount, purpose, created_by, created_at, status, note)
       VALUES (@reserve_id, @claim_ref, @reserve_type, @amount, @purpose, @created_by, @created_at, 'pending', @note)`
    )
    .run({ reserve_id, created_at: now(), note: input.note ?? "", ...input });
  return reserve_id;
}

export function approveReserve(reserve_id: string, approved_by: string): boolean {
  const info = getDb()
    .prepare(
      "UPDATE reserves SET approved_by=@approved_by, approved_at=@now, status='approved' WHERE reserve_id=@reserve_id"
    )
    .run({ approved_by, now: now(), reserve_id });
  return info.changes > 0;
}

export function releaseReserve(reserve_id: string, released_by: string, note = ""): boolean {
  const info = getDb()
    .prepare(
      "UPDATE reserves SET status='released', approved_by=@released_by, approved_at=@now, note=@note WHERE reserve_id=@reserve_id"
    )
    .run({ released_by, now: now(), note, reserve_id });
  return info.changes > 0;
}

export function getReserves(claim_ref: string): Reserve[] {
  return getDb()
    .prepare("SELECT * FROM reserves WHERE claim_ref=? ORDER BY created_at ASC")
    .all(claim_ref) as Reserve[];
}

export function getPendingReserves(): (Reserve & { claim?: Claim })[] {
  const rows = getDb()
    .prepare("SELECT * FROM reserves WHERE status='pending' ORDER BY created_at DESC")
    .all() as Reserve[];
  return rows.map((r) => ({ ...r, claim: getClaim(r.claim_ref) }));
}

export function getTotalReserves(claim_ref: string): number {
  const row = getDb()
    .prepare(
      "SELECT COALESCE(SUM(amount),0) t FROM reserves WHERE claim_ref=? AND status='approved'"
    )
    .get(claim_ref) as { t: number };
  return row.t;
}

// ---------------------------------------------------------------------------
// Diary
// ---------------------------------------------------------------------------

export function addDiaryEntry(input: {
  claim_ref: string;
  task: string;
  due_date: string;
  assigned_to: string;
  priority: "low" | "normal" | "high" | "urgent";
  created_by: string;
  note?: string;
}): string {
  const entry_id = id("DRY");
  getDb()
    .prepare(
      `INSERT INTO diary_entries (entry_id, claim_ref, task, due_date, assigned_to, priority, status, created_by, created_at, note)
       VALUES (@entry_id, @claim_ref, @task, @due_date, @assigned_to, @priority, 'open', @created_by, @created_at, @note)`
    )
    .run({ entry_id, created_at: now(), note: input.note ?? "", ...input });
  return entry_id;
}

export function completeDiaryEntry(entry_id: string): boolean {
  const info = getDb()
    .prepare("UPDATE diary_entries SET status='done', completed_at=? WHERE entry_id=?")
    .run(now(), entry_id);
  return info.changes > 0;
}

export function getDiaryEntries(claim_ref: string): DiaryEntry[] {
  return getDb()
    .prepare("SELECT * FROM diary_entries WHERE claim_ref=? ORDER BY due_date ASC")
    .all(claim_ref) as DiaryEntry[];
}

export function getOverdueEntries(assigned_to?: string): DiaryEntry[] {
  const today = new Date().toISOString().slice(0, 10);
  if (assigned_to) {
    return getDb()
      .prepare(
        "SELECT * FROM diary_entries WHERE status='open' AND due_date < ? AND assigned_to=? ORDER BY due_date"
      )
      .all(today, assigned_to) as DiaryEntry[];
  }
  return getDb()
    .prepare("SELECT * FROM diary_entries WHERE status='open' AND due_date < ? ORDER BY due_date")
    .all(today) as DiaryEntry[];
}

// ---------------------------------------------------------------------------
// Communications
// ---------------------------------------------------------------------------

export function logCommunication(input: {
  claim_ref: string;
  channel: "sms" | "call" | "email" | "letter" | "whatsapp";
  direction: "inbound" | "outbound";
  summary: string;
  created_by: string;
  contact_name?: string;
  contact_phone?: string;
  outcome?: string;
  consent?: boolean;
}): string {
  const comm_id = id("COM");
  getDb()
    .prepare(
      `INSERT INTO communications (comm_id, claim_ref, channel, direction, contact_name, contact_phone, summary, outcome, consent_obtained, created_by, created_at)
       VALUES (@comm_id, @claim_ref, @channel, @direction, @contact_name, @contact_phone, @summary, @outcome, @consent_obtained, @created_by, @created_at)`
    )
    .run({
      comm_id,
      created_at: now(),
      contact_name: input.contact_name ?? "",
      contact_phone: input.contact_phone ?? "",
      outcome: input.outcome ?? "",
      consent_obtained: input.consent === false ? "no" : "yes",
      claim_ref: input.claim_ref,
      channel: input.channel,
      direction: input.direction,
      summary: input.summary,
      created_by: input.created_by,
    });
  return comm_id;
}

export function getCommunications(claim_ref: string): Communication[] {
  return getDb()
    .prepare("SELECT * FROM communications WHERE claim_ref=? ORDER BY created_at DESC")
    .all(claim_ref) as Communication[];
}

// ---------------------------------------------------------------------------
// Expert assignments
// ---------------------------------------------------------------------------

export function assignExpert(input: {
  claim_ref: string;
  expert_type: "assessor" | "garage" | "investigator" | "loss_adjuster";
  expert_name: string;
  expert_phone?: string;
  expert_company?: string;
  assigned_by: string;
  estimated_cost?: number;
  note?: string;
}): string {
  const assignment_id = id("ASN");
  getDb()
    .prepare(
      `INSERT INTO expert_assignments (assignment_id, claim_ref, expert_type, expert_name, expert_phone, expert_company, status, assigned_by, assigned_at, estimated_cost, note)
       VALUES (@assignment_id, @claim_ref, @expert_type, @expert_name, @expert_phone, @expert_company, 'pending', @assigned_by, @assigned_at, @estimated_cost, @note)`
    )
    .run({
      assignment_id,
      assigned_at: now(),
      expert_phone: input.expert_phone ?? "",
      expert_company: input.expert_company ?? "",
      estimated_cost: input.estimated_cost ?? 0,
      note: input.note ?? "",
      claim_ref: input.claim_ref,
      expert_type: input.expert_type,
      expert_name: input.expert_name,
      assigned_by: input.assigned_by,
    });
  getDb()
    .prepare("UPDATE claims SET expert_type=? WHERE claim_ref=?")
    .run(input.expert_type === "loss_adjuster" ? "assessor" : input.expert_type, input.claim_ref);
  return assignment_id;
}

export function updateAssignmentStatus(
  assignment_id: string,
  status: ExpertAssignment["status"],
  actual_cost?: number
): boolean {
  const db = getDb();
  let info;
  if (status === "completed" && actual_cost !== undefined) {
    info = db
      .prepare(
        "UPDATE expert_assignments SET status=?, completed_at=?, actual_cost=? WHERE assignment_id=?"
      )
      .run(status, now(), actual_cost, assignment_id);
  } else if (status === "accepted") {
    info = db
      .prepare("UPDATE expert_assignments SET status=?, accepted_at=? WHERE assignment_id=?")
      .run(status, now(), assignment_id);
  } else {
    info = db
      .prepare("UPDATE expert_assignments SET status=? WHERE assignment_id=?")
      .run(status, assignment_id);
  }
  return info.changes > 0;
}

export function getAssignments(claim_ref: string): ExpertAssignment[] {
  return getDb()
    .prepare("SELECT * FROM expert_assignments WHERE claim_ref=? ORDER BY assigned_at DESC")
    .all(claim_ref) as ExpertAssignment[];
}

export function getAssignmentsByType(
  expert_type: ExpertAssignment["expert_type"]
): (ExpertAssignment & { claim?: Claim })[] {
  const rows = getDb()
    .prepare("SELECT * FROM expert_assignments WHERE expert_type=? ORDER BY assigned_at DESC")
    .all(expert_type) as ExpertAssignment[];
  return rows.map((r) => ({ ...r, claim: getClaim(r.claim_ref) }));
}

export function getAssignmentsForExpert(expert_name: string): (ExpertAssignment & {
  claim?: Claim;
})[] {
  const rows = getDb()
    .prepare("SELECT * FROM expert_assignments WHERE expert_name=? ORDER BY assigned_at DESC")
    .all(expert_name) as ExpertAssignment[];
  return rows.map((r) => ({ ...r, claim: getClaim(r.claim_ref) }));
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export function registerDocument(input: {
  claim_ref: string;
  doc_type: DocType;
  filename: string;
  file_size?: number;
  mime_type?: string;
  file_path?: string | null;
  uploaded_by: string;
  note?: string;
  ocr_status?: OcrStatus;
}): string {
  const db = getDb();
  const doc_id = id("DOC");
  const versionRow = db
    .prepare(
      "SELECT COALESCE(MAX(version),0) v FROM claim_documents WHERE claim_ref=? AND doc_type=?"
    )
    .get(input.claim_ref, input.doc_type) as { v: number };
  db.prepare(
    `INSERT INTO claim_documents (doc_id, claim_ref, doc_type, filename, file_size, mime_type, file_path, uploaded_by, uploaded_at, version, note, ocr_status)
     VALUES (@doc_id, @claim_ref, @doc_type, @filename, @file_size, @mime_type, @file_path, @uploaded_by, @uploaded_at, @version, @note, @ocr_status)`
  ).run({
    doc_id,
    uploaded_at: now(),
    version: versionRow.v + 1,
    file_size: input.file_size ?? 0,
    mime_type: input.mime_type ?? "application/octet-stream",
    file_path: input.file_path ?? null,
    note: input.note ?? "",
    ocr_status: input.ocr_status ?? "pending",
    claim_ref: input.claim_ref,
    doc_type: input.doc_type,
    filename: input.filename,
    uploaded_by: input.uploaded_by,
  });
  return doc_id;
}

export function getDocuments(claim_ref: string): ClaimDocument[] {
  return getDb()
    .prepare("SELECT * FROM claim_documents WHERE claim_ref=? ORDER BY uploaded_at DESC")
    .all(claim_ref) as ClaimDocument[];
}

export function getDocument(doc_id: string): ClaimDocument | undefined {
  return getDb().prepare("SELECT * FROM claim_documents WHERE doc_id=?").get(doc_id) as
    | ClaimDocument
    | undefined;
}

export function setDocumentFilePath(doc_id: string, file_path: string) {
  getDb().prepare("UPDATE claim_documents SET file_path=? WHERE doc_id=?").run(file_path, doc_id);
}

export function updateDocumentOcr(doc_id: string, ocr_status: OcrStatus, ocr_text: string | null) {
  getDb()
    .prepare("UPDATE claim_documents SET ocr_status=?, ocr_text=? WHERE doc_id=?")
    .run(ocr_status, ocr_text, doc_id);
}

export function updateDocumentExif(doc_id: string, exif_json: string | null) {
  getDb().prepare("UPDATE claim_documents SET exif_json=? WHERE doc_id=?").run(exif_json, doc_id);
}

// ---------------------------------------------------------------------------
// Settlements
// ---------------------------------------------------------------------------

const WHT_RATES: Record<Settlement["payee_type"], number> = {
  assessor: 0.05,
  garage: 0.05,
  investigator: 0.05,
  spare_parts: 0.1,
  third_party: 0.0,
  insured: 0.0,
};

export function recommendSettlement(input: {
  claim_ref: string;
  amount: number;
  payee_name: string;
  payee_type: Settlement["payee_type"];
  recommended_by: string;
  note?: string;
}): string {
  const settlement_id = id("STL");
  const wht_rate = WHT_RATES[input.payee_type] ?? 0;
  const wht_amount = Math.round(input.amount * wht_rate * 100) / 100;
  const net_amount = Math.round((input.amount - wht_amount) * 100) / 100;
  getDb()
    .prepare(
      `INSERT INTO settlements (settlement_id, claim_ref, settlement_type, amount, payee_name, payee_type, wht_rate, wht_amount, net_amount, status, recommended_by, recommended_at, note)
       VALUES (@settlement_id, @claim_ref, 'officer_recommend', @amount, @payee_name, @payee_type, @wht_rate, @wht_amount, @net_amount, 'pending', @recommended_by, @recommended_at, @note)`
    )
    .run({
      settlement_id,
      recommended_at: now(),
      wht_rate,
      wht_amount,
      net_amount,
      note: input.note ?? "",
      claim_ref: input.claim_ref,
      amount: input.amount,
      payee_name: input.payee_name,
      payee_type: input.payee_type,
      recommended_by: input.recommended_by,
    });
  return settlement_id;
}

export function approveSettlement(settlement_id: string, approved_by: string): boolean {
  const info = getDb()
    .prepare(
      "UPDATE settlements SET status='approved', approved_by=?, approved_at=? WHERE settlement_id=?"
    )
    .run(approved_by, now(), settlement_id);
  return info.changes > 0;
}

export function markSettlementPaid(settlement_id: string, bank_ref: string): boolean {
  const info = getDb()
    .prepare("UPDATE settlements SET status='paid', paid_at=?, bank_ref=? WHERE settlement_id=?")
    .run(now(), bank_ref, settlement_id);
  return info.changes > 0;
}

export function getSettlements(claim_ref: string): Settlement[] {
  return getDb()
    .prepare("SELECT * FROM settlements WHERE claim_ref=? ORDER BY recommended_at ASC")
    .all(claim_ref) as Settlement[];
}

export function getSettlementsByStatus(status: Settlement["status"]): (Settlement & {
  claim?: Claim;
})[] {
  const rows = getDb()
    .prepare("SELECT * FROM settlements WHERE status=? ORDER BY recommended_at DESC")
    .all(status) as Settlement[];
  return rows.map((r) => ({ ...r, claim: getClaim(r.claim_ref) }));
}

// ---------------------------------------------------------------------------
// RFQs / Bids
// ---------------------------------------------------------------------------

export function getRfqsForClaim(claim_ref: string): Rfq[] {
  return getDb()
    .prepare("SELECT * FROM rfqs WHERE claim_ref=? ORDER BY created_at DESC")
    .all(claim_ref) as Rfq[];
}

export function listOpenRfqs(): Rfq[] {
  return getDb()
    .prepare("SELECT * FROM rfqs WHERE status='open' ORDER BY created_at DESC")
    .all() as Rfq[];
}

export function getRfq(rfq_ref: string): Rfq | undefined {
  return getDb().prepare("SELECT * FROM rfqs WHERE rfq_ref=?").get(rfq_ref) as Rfq | undefined;
}

export function getBids(rfq_ref: string): Bid[] {
  return getDb()
    .prepare("SELECT * FROM bids WHERE rfq_ref=? ORDER BY unit_price ASC")
    .all(rfq_ref) as Bid[];
}

export function getBidsByProvider(provider: string): (Bid & { rfq?: Rfq })[] {
  const rows = getDb()
    .prepare("SELECT * FROM bids WHERE provider=? ORDER BY submitted_at DESC")
    .all(provider) as Bid[];
  return rows.map((b) => ({ ...b, rfq: getRfq(b.rfq_ref) }));
}

export function submitBid(input: {
  rfq_ref: string;
  provider: string;
  brand: string;
  condition: string;
  unit_price: number;
  lead_days: number;
  warranty: string;
  rating: number;
}): string {
  const bid_ref = id("BID");
  getDb()
    .prepare(
      `INSERT INTO bids (bid_ref, rfq_ref, provider, brand, condition, unit_price, lead_days, warranty, rating, submitted_at, status)
       VALUES (@bid_ref, @rfq_ref, @provider, @brand, @condition, @unit_price, @lead_days, @warranty, @rating, @submitted_at, 'submitted')`
    )
    .run({ bid_ref, submitted_at: now(), ...input });
  return bid_ref;
}

export function awardBid(bid_ref: string, rfq_ref: string): void {
  const db = getDb();
  const tx = db.transaction(() => {
    db.prepare("UPDATE bids SET status='won' WHERE bid_ref=?").run(bid_ref);
    db.prepare("UPDATE bids SET status='lost' WHERE rfq_ref=? AND bid_ref<>?").run(
      rfq_ref,
      bid_ref
    );
    db.prepare("UPDATE rfqs SET status='awarded' WHERE rfq_ref=?").run(rfq_ref);
  });
  tx();
}

// ---------------------------------------------------------------------------
// DocuSeal submissions
// ---------------------------------------------------------------------------

export function createDocusealRecord(input: {
  claim_ref: string;
  workflow: DocusealWorkflow;
  form_key?: ClaimFormKey | null;
  template_id: string | null;
  docuseal_submission_id: string | null;
  signer_name: string;
  signer_email: string;
  status: DocusealSubmission["status"];
  embed_src: string | null;
  created_by: string;
}): string {
  const submission_id = id("SIG");
  getDb()
    .prepare(
      `INSERT INTO docuseal_submissions (submission_id, claim_ref, workflow, form_key, template_id, docuseal_submission_id, signer_name, signer_email, status, embed_src, created_by, created_at)
       VALUES (@submission_id, @claim_ref, @workflow, @form_key, @template_id, @docuseal_submission_id, @signer_name, @signer_email, @status, @embed_src, @created_by, @created_at)`
    )
    .run({ submission_id, created_at: now(), form_key: input.form_key ?? null, ...input });
  return submission_id;
}

export function getDocusealByWorkflow(
  workflow: DocusealWorkflow
): (DocusealSubmission & { claim?: Claim })[] {
  const rows = getDb()
    .prepare("SELECT * FROM docuseal_submissions WHERE workflow=? ORDER BY created_at DESC")
    .all(workflow) as DocusealSubmission[];
  return rows.map((r) => ({ ...r, claim: getClaim(r.claim_ref) }));
}

export function getDocusealSubmissions(claim_ref: string): DocusealSubmission[] {
  return getDb()
    .prepare("SELECT * FROM docuseal_submissions WHERE claim_ref=? ORDER BY created_at DESC")
    .all(claim_ref) as DocusealSubmission[];
}

export function markDocusealCompleted(submission_id: string): boolean {
  const info = getDb()
    .prepare(
      "UPDATE docuseal_submissions SET status='completed', completed_at=? WHERE submission_id=?"
    )
    .run(now(), submission_id);
  return info.changes > 0;
}

// ---------------------------------------------------------------------------
// SLA
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Investigator "Notification of Incident" reports (7th claim form — filed by
// the investigator, not the client; feeds the fraud-screening engine)
// ---------------------------------------------------------------------------

export function fileInvestigatorReport(input: {
  claim_ref: string;
  investigator_name: string;
  mode_of_report?: string;
  accident_datetime?: string;
  location?: string;
  police_station?: string;
  injured_count?: number;
  deceased_count?: number;
  fraud_suspected: "yes" | "no";
  fraud_basis?: string;
  created_by: string;
}): string {
  const report_id = id("INV");
  getDb()
    .prepare(
      `INSERT INTO investigator_reports (report_id, claim_ref, investigator_name, mode_of_report, accident_datetime, location, police_station, injured_count, deceased_count, fraud_suspected, fraud_basis, created_by, created_at)
       VALUES (@report_id, @claim_ref, @investigator_name, @mode_of_report, @accident_datetime, @location, @police_station, @injured_count, @deceased_count, @fraud_suspected, @fraud_basis, @created_by, @created_at)`
    )
    .run({
      report_id,
      created_at: now(),
      mode_of_report: input.mode_of_report ?? "",
      accident_datetime: input.accident_datetime ?? "",
      location: input.location ?? "",
      police_station: input.police_station ?? "",
      injured_count: input.injured_count ?? 0,
      deceased_count: input.deceased_count ?? 0,
      fraud_basis: input.fraud_basis ?? "",
      claim_ref: input.claim_ref,
      investigator_name: input.investigator_name,
      fraud_suspected: input.fraud_suspected,
      created_by: input.created_by,
    });
  return report_id;
}

export function getInvestigatorReports(claim_ref: string): InvestigatorReport[] {
  return getDb()
    .prepare("SELECT * FROM investigator_reports WHERE claim_ref=? ORDER BY created_at DESC")
    .all(claim_ref) as InvestigatorReport[];
}

// ---------------------------------------------------------------------------
// Fraud assessments (Stage 5 — Fraud Screening and Triage)
// ---------------------------------------------------------------------------

export function createFraudAssessment(input: {
  claim_ref: string;
  score: number;
  risk_band: FraudRiskBand;
  indicators_json: string;
  recommended_action: string;
  computed_by?: string;
}): string {
  const assessment_id = id("FRD");
  getDb()
    .prepare(
      `INSERT INTO fraud_assessments (assessment_id, claim_ref, score, risk_band, indicators_json, recommended_action, computed_at, computed_by, review_status)
       VALUES (@assessment_id, @claim_ref, @score, @risk_band, @indicators_json, @recommended_action, @computed_at, @computed_by, 'pending_review')`
    )
    .run({
      assessment_id,
      computed_at: now(),
      computed_by: input.computed_by ?? "system",
      claim_ref: input.claim_ref,
      score: input.score,
      risk_band: input.risk_band,
      indicators_json: input.indicators_json,
      recommended_action: input.recommended_action,
    });
  return assessment_id;
}

export function getFraudAssessments(claim_ref: string): FraudAssessment[] {
  return getDb()
    .prepare("SELECT * FROM fraud_assessments WHERE claim_ref=? ORDER BY computed_at DESC")
    .all(claim_ref) as FraudAssessment[];
}

export function getLatestFraudAssessment(claim_ref: string): FraudAssessment | undefined {
  return getDb()
    .prepare("SELECT * FROM fraud_assessments WHERE claim_ref=? ORDER BY computed_at DESC LIMIT 1")
    .get(claim_ref) as FraudAssessment | undefined;
}

export function getFraudQueue(band?: FraudRiskBand): (FraudAssessment & { claim?: Claim })[] {
  const rows = band
    ? (getDb()
        .prepare(
          "SELECT * FROM fraud_assessments WHERE review_status='pending_review' AND risk_band=? ORDER BY score DESC"
        )
        .all(band) as FraudAssessment[])
    : (getDb()
        .prepare(
          "SELECT * FROM fraud_assessments WHERE review_status='pending_review' ORDER BY score DESC"
        )
        .all() as FraudAssessment[]);
  return rows.map((r) => ({ ...r, claim: getClaim(r.claim_ref) }));
}

export function reviewFraudAssessment(
  assessment_id: string,
  reviewed_by: string,
  decision: NonNullable<FraudAssessment["review_decision"]>,
  review_note = ""
): boolean {
  const info = getDb()
    .prepare(
      `UPDATE fraud_assessments SET review_status='reviewed', reviewed_by=?, reviewed_at=?, review_decision=?, review_note=? WHERE assessment_id=?`
    )
    .run(reviewed_by, now(), decision, review_note, assessment_id);
  return info.changes > 0;
}

// ---------------------------------------------------------------------------
// Configuration engine — versioned / effective-dated / maker-checker approved
// ---------------------------------------------------------------------------

export function getActiveConfig(config_key: string): ConfigItem | undefined {
  return getDb()
    .prepare(
      "SELECT * FROM configurations WHERE config_key=? AND status='approved' ORDER BY version DESC LIMIT 1"
    )
    .get(config_key) as ConfigItem | undefined;
}

export function getAllActiveConfigs(): ConfigItem[] {
  return getDb()
    .prepare(
      `SELECT c.* FROM configurations c
       INNER JOIN (SELECT config_key, MAX(version) mv FROM configurations WHERE status='approved' GROUP BY config_key) latest
       ON c.config_key = latest.config_key AND c.version = latest.mv
       ORDER BY c.config_key ASC`
    )
    .all() as ConfigItem[];
}

export function getConfigHistory(config_key: string): ConfigItem[] {
  return getDb()
    .prepare("SELECT * FROM configurations WHERE config_key=? ORDER BY version DESC")
    .all(config_key) as ConfigItem[];
}

export function getPendingConfigs(): ConfigItem[] {
  return getDb()
    .prepare("SELECT * FROM configurations WHERE status='pending_approval' ORDER BY proposed_at DESC")
    .all() as ConfigItem[];
}

/** Seed or system-initialise a config at version 1, already approved. */
export function seedConfig(config_key: string, value: unknown, note = "Initial default") {
  const existing = getConfigHistory(config_key);
  if (existing.length > 0) return;
  getDb()
    .prepare(
      `INSERT INTO configurations (config_key, version, value_json, status, proposed_by, proposed_at, approved_by, approved_at, effective_date, note)
       VALUES (@config_key, 1, @value_json, 'approved', 'system', @ts, 'system', @ts, @ts, @note)`
    )
    .run({ config_key, value_json: JSON.stringify(value), ts: now(), note });
}

/** Maker step: propose a new version of a config (does not take effect until approved). */
export function proposeConfig(input: {
  config_key: string;
  value: unknown;
  proposed_by: string;
  note?: string;
}): number {
  const db = getDb();
  const maxVersion = (
    db
      .prepare("SELECT COALESCE(MAX(version),0) v FROM configurations WHERE config_key=?")
      .get(input.config_key) as { v: number }
  ).v;
  const version = maxVersion + 1;
  db.prepare(
    `INSERT INTO configurations (config_key, version, value_json, status, proposed_by, proposed_at, effective_date, note)
     VALUES (@config_key, @version, @value_json, 'pending_approval', @proposed_by, @ts, @ts, @note)`
  ).run({
    config_key: input.config_key,
    version,
    value_json: JSON.stringify(input.value),
    proposed_by: input.proposed_by,
    ts: now(),
    note: input.note ?? "",
  });
  return version;
}

/** Checker step: a *different* user approves the pending version (maker-checker). */
export function approveConfig(
  config_key: string,
  version: number,
  approved_by: string
): { ok: boolean; error?: string } {
  const db = getDb();
  const row = db
    .prepare("SELECT * FROM configurations WHERE config_key=? AND version=?")
    .get(config_key, version) as ConfigItem | undefined;
  if (!row) return { ok: false, error: "Configuration version not found." };
  if (row.status !== "pending_approval") return { ok: false, error: "This version is not awaiting approval." };
  if (row.proposed_by === approved_by) {
    return { ok: false, error: "Maker-checker: the approver must be different from the person who proposed the change." };
  }
  db.prepare(
    "UPDATE configurations SET status='approved', approved_by=?, approved_at=? WHERE config_key=? AND version=?"
  ).run(approved_by, now(), config_key, version);
  return { ok: true };
}

export function rejectConfig(config_key: string, version: number): boolean {
  const info = getDb()
    .prepare("DELETE FROM configurations WHERE config_key=? AND version=? AND status='pending_approval'")
    .run(config_key, version);
  return info.changes > 0;
}

export function getSlaStatus(date_reported: string) {
  const submitted = new Date(date_reported);
  const ackDeadline = new Date(submitted.getTime() + 14 * 86400000);
  const settleDeadline = new Date(submitted.getTime() + 30 * 86400000);
  const nowD = new Date();
  const daysTo = (d: Date) => Math.max(0, Math.ceil((d.getTime() - nowD.getTime()) / 86400000));
  return {
    acknowledged_overdue: nowD >= ackDeadline,
    settlement_overdue: nowD >= settleDeadline,
    ack_deadline: ackDeadline.toISOString().slice(0, 10),
    settle_deadline: settleDeadline.toISOString().slice(0, 10),
    days_to_ack: daysTo(ackDeadline),
    days_to_settle: daysTo(settleDeadline),
  };
}
