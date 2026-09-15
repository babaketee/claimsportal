"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { requireSession } from "@/lib/session";
import * as repo from "@/lib/repo";
import type { ConfigItem, DocType, Settlement } from "@/lib/types";
import { runFraudScreening, triageNewClaim } from "@/lib/fraud";
import { runOcr } from "@/lib/ocr";
import { extractPhotoMetadata } from "@/lib/exif";
import { saveUploadedFile } from "@/lib/storage";

function refresh(claim_ref: string) {
  revalidatePath(`/app/claims/${claim_ref}`);
  revalidatePath("/app");
}

export async function setReserveAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  repo.setReserve({
    claim_ref,
    reserve_type: String(formData.get("reserve_type")) as "initial" | "supplemental",
    amount: Number(formData.get("amount")),
    purpose: String(formData.get("purpose")),
    created_by: session.email,
    note: String(formData.get("note") ?? ""),
  });
  refresh(claim_ref);
}

export async function approveReserveAction(reserve_id: string, claim_ref: string) {
  const session = await requireSession();
  repo.approveReserve(reserve_id, session.email);
  refresh(claim_ref);
}

export async function releaseReserveAction(reserve_id: string, claim_ref: string) {
  const session = await requireSession();
  repo.releaseReserve(reserve_id, session.email, "Released");
  refresh(claim_ref);
}

export async function assignExpertAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  repo.assignExpert({
    claim_ref,
    expert_type: String(formData.get("expert_type")) as never,
    expert_name: String(formData.get("expert_name")),
    expert_phone: String(formData.get("expert_phone") ?? ""),
    assigned_by: session.email,
    estimated_cost: Number(formData.get("estimated_cost") ?? 0),
    note: String(formData.get("note") ?? ""),
  });
  refresh(claim_ref);
}

export async function updateAssignmentStatusAction(
  assignment_id: string,
  status: "accepted" | "in_progress" | "completed" | "rejected",
  claim_ref: string,
  actual_cost?: number
) {
  await requireSession();
  repo.updateAssignmentStatus(assignment_id, status, actual_cost);
  refresh(claim_ref);
}

export async function logCommunicationAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  repo.logCommunication({
    claim_ref,
    channel: String(formData.get("channel")) as never,
    direction: String(formData.get("direction")) as never,
    summary: String(formData.get("summary")),
    created_by: session.email,
    contact_name: String(formData.get("contact_name") ?? ""),
    contact_phone: String(formData.get("contact_phone") ?? ""),
    outcome: String(formData.get("outcome") ?? ""),
    consent: formData.get("consent") === "on",
  });
  refresh(claim_ref);
}

export async function addDiaryEntryAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  repo.addDiaryEntry({
    claim_ref,
    task: String(formData.get("task")),
    due_date: String(formData.get("due_date")),
    assigned_to: String(formData.get("assigned_to") ?? session.email),
    priority: String(formData.get("priority")) as never,
    created_by: session.email,
    note: String(formData.get("note") ?? ""),
  });
  refresh(claim_ref);
}

export async function completeDiaryEntryAction(entry_id: string, claim_ref: string) {
  await requireSession();
  repo.completeDiaryEntry(entry_id);
  refresh(claim_ref);
}

export async function recommendSettlementAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  repo.recommendSettlement({
    claim_ref,
    amount: Number(formData.get("amount")),
    payee_name: String(formData.get("payee_name")),
    payee_type: String(formData.get("payee_type")) as Settlement["payee_type"],
    recommended_by: session.email,
    note: String(formData.get("note") ?? ""),
  });
  repo.updateClaimStatus(claim_ref, "Pending approval", session.email, "Settlement recommended by claims officer");
  refresh(claim_ref);
}

export async function approveSettlementAction(settlement_id: string, claim_ref: string) {
  const session = await requireSession();
  repo.approveSettlement(settlement_id, session.email);
  repo.updateClaimStatus(claim_ref, "Approved", session.email, "Settlement approved by Head of Claims");
  refresh(claim_ref);
}

/**
 * Recommendation R5: the signed discharge voucher is a hard precondition to
 * payment. This gate blocks the Finance payment step until a completed
 * settlement_discharge DocuSeal submission exists for the claim.
 */
function hasCompletedDischargeVoucher(claim_ref: string): boolean {
  return repo
    .getDocusealSubmissions(claim_ref)
    .some((s) => s.workflow === "settlement_discharge" && s.status === "completed");
}

export async function markSettlementPaidAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  const settlement_id = String(formData.get("settlement_id"));

  if (!hasCompletedDischargeVoucher(claim_ref)) {
    repo.addDiaryEntry({
      claim_ref,
      task: "BLOCKED: payment cannot be released — signed discharge voucher is missing",
      due_date: new Date().toISOString().slice(0, 10),
      assigned_to: session.email,
      priority: "urgent",
      created_by: "system",
      note: "Design principle: the discharge voucher is a hard precondition to payment (recommendation R5).",
    });
    refresh(claim_ref);
    return;
  }

  repo.markSettlementPaid(settlement_id, String(formData.get("bank_ref")));
  repo.updateClaimStatus(claim_ref, "Pending payment", session.email, "Payment instruction raised");
  repo.updateClaimStatus(claim_ref, "Paid", session.email, "Settlement disbursed (discharge voucher confirmed signed)");
  refresh(claim_ref);
}

export async function closeClaimAction(claim_ref: string) {
  const session = await requireSession();
  repo.updateClaimStatus(claim_ref, "Closed", session.email, "Claim closed after settlement / repudiation confirmed");
  refresh(claim_ref);
}

export async function fileNewClaimAction(formData: FormData) {
  const session = await requireSession();
  const category = String(formData.get("category")) as "Motor" | "Business";
  const year = new Date().getFullYear();
  const seq = Math.floor(Math.random() * 9000 + 1000);
  const claim_ref = `CLM-${year}-${category === "Motor" ? "M" : "B"}${seq}`;
  const dateOfLoss = String(formData.get("date_of_loss") || new Date().toISOString().slice(0, 10));

  repo.createClaim({
    claim_ref,
    category,
    claim_type: String(formData.get("claim_type")),
    status: "Submitted",
    policy_number: String(formData.get("policy_number") || "PENDING"),
    insured_name: session.full_name,
    client_email: session.email,
    vehicle_reg: category === "Motor" ? String(formData.get("vehicle_reg") || "") : null,
    location: String(formData.get("location")),
    date_of_loss: dateOfLoss,
    date_reported: new Date().toISOString().slice(0, 10),
    claim_amount: Number(formData.get("claim_amount") ?? 0),
    urgency: "Medium",
    description: String(formData.get("description")),
    assigned_officer: "officer@insure.demo",
    expert_type: null,
  });
  repo.logCommunication({
    claim_ref,
    channel: "email",
    direction: "inbound",
    summary: "First notification of loss (FNOL) submitted via client portal",
    created_by: session.email,
    contact_name: session.full_name,
  });

  await triageNewClaim(claim_ref);

  refresh(claim_ref);
  redirect(`/app/claims/${claim_ref}`);
}

export async function updateClaimStatusAction(claim_ref: string, status: string) {
  const session = await requireSession();
  repo.updateClaimStatus(claim_ref, status, session.email, "Manual status change");
  refresh(claim_ref);
}

export async function awardBidAction(bid_ref: string, rfq_ref: string, claim_ref: string) {
  await requireSession();
  repo.awardBid(bid_ref, rfq_ref);
  refresh(claim_ref);
}

export async function submitBidAction(formData: FormData) {
  await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  repo.submitBid({
    rfq_ref: String(formData.get("rfq_ref")),
    provider: String(formData.get("provider")),
    brand: String(formData.get("brand")),
    condition: String(formData.get("condition")),
    unit_price: Number(formData.get("unit_price")),
    lead_days: Number(formData.get("lead_days")),
    warranty: String(formData.get("warranty")),
    rating: Number(formData.get("rating") ?? 4),
  });
  refresh(claim_ref);
}

// ---------------------------------------------------------------------------
// Documents: upload + OCR + EXIF metadata
// ---------------------------------------------------------------------------

export async function uploadDocumentAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  const doc_type = String(formData.get("doc_type")) as DocType;
  const file = formData.get("file") as File | null;

  if (!file || file.size === 0) {
    refresh(claim_ref);
    return;
  }

  const doc_id_placeholder = repo.registerDocument({
    claim_ref,
    doc_type,
    filename: file.name,
    file_size: file.size,
    mime_type: file.type || "application/octet-stream",
    uploaded_by: session.email,
    ocr_status: "pending",
  });

  const { filePath } = await saveUploadedFile(claim_ref, doc_id_placeholder, file);
  repo.setDocumentFilePath(doc_id_placeholder, filePath);

  const claim = repo.getClaim(claim_ref);

  // OCR (best-effort — never blocks the upload if it fails or is unsupported).
  const ocrResult = await runOcr(filePath, file.type || "application/octet-stream");
  repo.updateDocumentOcr(doc_id_placeholder, ocrResult.status, ocrResult.text);

  // EXIF / photo metadata retrieval, compared against the claimed loss date.
  const metadata = await extractPhotoMetadata(filePath, file.type || "", claim?.date_of_loss ?? null);
  if (metadata) {
    repo.updateDocumentExif(doc_id_placeholder, JSON.stringify(metadata));
  }

  // New evidence can change the fraud picture — re-run screening.
  await runFraudScreening(claim_ref, "system");

  refresh(claim_ref);
}

// ---------------------------------------------------------------------------
// Fraud screening & human review
// ---------------------------------------------------------------------------

export async function runFraudAssessmentAction(claim_ref: string) {
  await requireSession();
  await runFraudScreening(claim_ref, "system");
  refresh(claim_ref);
}

export async function reviewFraudAssessmentAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));
  const assessment_id = String(formData.get("assessment_id"));
  const decision = String(formData.get("decision")) as "proceed" | "escalate_to_investigator" | "cleared";
  const note = String(formData.get("review_note") ?? "");

  repo.reviewFraudAssessment(assessment_id, session.email, decision, note);

  if (decision === "proceed" || decision === "cleared") {
    repo.updateClaimStatus(
      claim_ref,
      "Under investigation and assessment",
      session.email,
      `Fraud review cleared (${decision}): ${note || "no additional notes"}`
    );
  } else if (decision === "escalate_to_investigator") {
    repo.assignExpert({
      claim_ref,
      expert_type: "investigator",
      expert_name: "Sentinel Risk Investigators",
      assigned_by: session.email,
      note: `Escalated from fraud review: ${note}`,
    });
    repo.updateClaimStatus(
      claim_ref,
      "Under investigation and assessment",
      session.email,
      `Escalated to investigator following fraud review: ${note || "no additional notes"}`
    );
  }

  refresh(claim_ref);
}

// ---------------------------------------------------------------------------
// Investigator "Notification of Incident" report (7th claim form)
// ---------------------------------------------------------------------------

export async function fileInvestigatorReportAction(formData: FormData) {
  const session = await requireSession();
  const claim_ref = String(formData.get("claim_ref"));

  repo.fileInvestigatorReport({
    claim_ref,
    investigator_name: String(formData.get("investigator_name") || session.full_name),
    mode_of_report: String(formData.get("mode_of_report") ?? ""),
    accident_datetime: String(formData.get("accident_datetime") ?? ""),
    location: String(formData.get("location") ?? ""),
    police_station: String(formData.get("police_station") ?? ""),
    injured_count: Number(formData.get("injured_count") ?? 0),
    deceased_count: Number(formData.get("deceased_count") ?? 0),
    fraud_suspected: (formData.get("fraud_suspected") === "yes" ? "yes" : "no") as "yes" | "no",
    fraud_basis: String(formData.get("fraud_basis") ?? ""),
    created_by: session.email,
  });

  await runFraudScreening(claim_ref, "system");
  refresh(claim_ref);
}

// ---------------------------------------------------------------------------
// Configuration engine — maker-checker
// ---------------------------------------------------------------------------

export async function proposeConfigAction(formData: FormData) {
  const session = await requireSession();
  const config_key = String(formData.get("config_key"));
  const value_json = String(formData.get("value_json"));
  let value: unknown;
  try {
    value = JSON.parse(value_json);
  } catch {
    return;
  }
  repo.proposeConfig({
    config_key,
    value,
    proposed_by: session.email,
    note: String(formData.get("note") ?? ""),
  });
  revalidatePath("/app/admin/config");
}

export async function approveConfigAction(config_key: string, version: number) {
  const session = await requireSession();
  repo.approveConfig(config_key, version, session.email);
  revalidatePath("/app/admin/config");
}

export async function rejectConfigAction(config_key: string, version: number) {
  await requireSession();
  repo.rejectConfig(config_key, version);
  revalidatePath("/app/admin/config");
}

export type { ConfigItem };
