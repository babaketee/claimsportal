import { Table } from "@/components/ui/Table";
import { StatusBadge, Badge } from "@/components/ui/Badge";
import { kes } from "@/components/ui/Stat";
import type {
  Claim,
  ClaimDocument,
  Communication,
  DiaryEntry,
  ExpertAssignment,
  Reserve,
  Rfq,
  Bid,
  Settlement,
  Role,
} from "@/lib/types";
import {
  setReserveAction,
  approveReserveAction,
  releaseReserveAction,
  assignExpertAction,
  updateAssignmentStatusAction,
  logCommunicationAction,
  addDiaryEntryAction,
  completeDiaryEntryAction,
  recommendSettlementAction,
  approveSettlementAction,
  markSettlementPaidAction,
  awardBidAction,
  submitBidAction,
  uploadDocumentAction,
} from "@/app/actions/claims";

const fmt = (d: string | null) => (d ? new Date(d).toLocaleString() : "—");

// ---------------------------------------------------------------------------
// Reserves
// ---------------------------------------------------------------------------
export function ReservesPanel({
  claim,
  reserves,
  canManage,
}: {
  claim: Claim;
  reserves: Reserve[];
  canManage: boolean;
}) {
  const approvedTotal = reserves
    .filter((r) => r.status === "approved")
    .reduce((s, r) => s + r.amount, 0);

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase text-black/45">Total Reserves</p>
          <p className="mt-1 text-xl font-bold text-brand-green">{kes(approvedTotal)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs font-semibold uppercase text-black/45">Claim Amount</p>
          <p className="mt-1 text-xl font-bold text-brand-ink">{kes(claim.claim_amount)}</p>
        </div>
      </div>

      <Table
        columns={[
          { key: "id", label: "Reserve" },
          { key: "type", label: "Type" },
          { key: "amount", label: "Amount", align: "right" },
          { key: "purpose", label: "Purpose" },
          { key: "status", label: "Status" },
          { key: "created", label: "Created" },
          ...(canManage ? [{ key: "actions", label: "" }] : []),
        ]}
        rows={reserves.map((r) => ({
          id: <span className="font-mono text-xs">{r.reserve_id}</span>,
          type: r.reserve_type,
          amount: kes(r.amount),
          purpose: r.purpose,
          status: <StatusBadge status={r.status} />,
          created: fmt(r.created_at),
          actions: canManage && r.status === "pending" && (
            <div className="flex justify-end gap-2">
              <form action={approveReserveAction.bind(null, r.reserve_id, claim.claim_ref)}>
                <button className="btn-ghost !px-2 !py-1 text-xs">Approve</button>
              </form>
              <form action={releaseReserveAction.bind(null, r.reserve_id, claim.claim_ref)}>
                <button className="btn-ghost !px-2 !py-1 text-xs">Release</button>
              </form>
            </div>
          ),
        }))}
        emptyLabel="No reserves set yet."
      />

      {canManage && (
        <form action={setReserveAction} className="card space-y-3 p-4">
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <p className="text-sm font-bold">Set a reserve</p>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="field-label">Type</label>
              <select name="reserve_type" className="field-input">
                <option value="initial">Initial</option>
                <option value="supplemental">Supplemental</option>
              </select>
            </div>
            <div>
              <label className="field-label">Amount (KES)</label>
              <input name="amount" type="number" min={0} step={1000} required className="field-input" />
            </div>
            <div>
              <label className="field-label">Purpose</label>
              <select name="purpose" className="field-input">
                <option value="assessment">Assessment</option>
                <option value="repair">Repair</option>
                <option value="legal">Legal</option>
                <option value="investigation">Investigation</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div>
            <label className="field-label">Note</label>
            <textarea name="note" className="field-input" rows={2} />
          </div>
          <button className="btn-primary">Set Reserve</button>
        </form>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Diary + communications
// ---------------------------------------------------------------------------
export function DiaryPanel({
  claim,
  diary,
  canManage,
}: {
  claim: Claim;
  diary: DiaryEntry[];
  canManage: boolean;
}) {
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div className="space-y-5">
      <Table
        columns={[
          { key: "task", label: "Task" },
          { key: "due", label: "Due" },
          { key: "assigned", label: "Assigned To" },
          { key: "priority", label: "Priority" },
          { key: "status", label: "Status" },
          ...(canManage ? [{ key: "actions", label: "" }] : []),
        ]}
        rows={diary.map((d) => ({
          task: d.task,
          due: (
            <span className={d.status === "open" && d.due_date < today ? "font-semibold text-brand-red" : ""}>
              {d.due_date}
            </span>
          ),
          assigned: d.assigned_to,
          priority: <Badge tone={d.priority === "urgent" || d.priority === "high" ? "red" : "neutral"}>{d.priority}</Badge>,
          status: <StatusBadge status={d.status} />,
          actions: canManage && d.status === "open" && (
            <form action={completeDiaryEntryAction.bind(null, d.entry_id, claim.claim_ref)}>
              <button className="btn-ghost !px-2 !py-1 text-xs">Mark done</button>
            </form>
          ),
        }))}
        emptyLabel="No diary entries."
      />
      {canManage && (
        <form action={addDiaryEntryAction} className="card space-y-3 p-4">
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <p className="text-sm font-bold">Add diary entry</p>
          <div>
            <label className="field-label">Task</label>
            <input name="task" required className="field-input" />
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="field-label">Due date</label>
              <input name="due_date" type="date" required className="field-input" />
            </div>
            <div>
              <label className="field-label">Assigned to</label>
              <input name="assigned_to" defaultValue={claim.assigned_officer ?? ""} className="field-input" />
            </div>
            <div>
              <label className="field-label">Priority</label>
              <select name="priority" className="field-input">
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>
          <button className="btn-primary">Add Entry</button>
        </form>
      )}
    </div>
  );
}

export function CommsPanel({
  claim,
  comms,
  canManage,
}: {
  claim: Claim;
  comms: Communication[];
  canManage: boolean;
}) {
  return (
    <div className="space-y-5">
      <Table
        columns={[
          { key: "channel", label: "Channel" },
          { key: "direction", label: "Direction" },
          { key: "contact", label: "Contact" },
          { key: "summary", label: "Summary" },
          { key: "when", label: "When" },
        ]}
        rows={comms.map((c) => ({
          channel: <Badge tone="blue">{c.channel}</Badge>,
          direction: c.direction,
          contact: c.contact_name || "—",
          summary: c.summary,
          when: fmt(c.created_at),
        }))}
        emptyLabel="No communications logged."
      />
      {canManage && (
        <form action={logCommunicationAction} className="card space-y-3 p-4">
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <p className="text-sm font-bold">Log communication</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="field-label">Channel</label>
              <select name="channel" className="field-input">
                <option value="sms">SMS</option>
                <option value="call">Call</option>
                <option value="email">Email</option>
                <option value="letter">Letter</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
            </div>
            <div>
              <label className="field-label">Direction</label>
              <select name="direction" className="field-input">
                <option value="outbound">Outbound</option>
                <option value="inbound">Inbound</option>
              </select>
            </div>
            <div>
              <label className="field-label">Contact name</label>
              <input name="contact_name" defaultValue={claim.insured_name} className="field-input" />
            </div>
            <div>
              <label className="field-label">Phone / email</label>
              <input name="contact_phone" className="field-input" />
            </div>
          </div>
          <div>
            <label className="field-label">Summary</label>
            <textarea name="summary" required rows={2} className="field-input" />
          </div>
          <label className="flex items-center gap-2 text-sm text-black/60">
            <input type="checkbox" name="consent" defaultChecked /> DPA 2019 consent obtained
          </label>
          <button className="btn-primary">Log Communication</button>
        </form>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Assignments
// ---------------------------------------------------------------------------
export function AssignmentsPanel({
  claim,
  assignments,
  canAssign,
  role,
}: {
  claim: Claim;
  assignments: ExpertAssignment[];
  canAssign: boolean;
  role: Role;
}) {
  const canUpdateOwn = ["assessor", "garage", "investigator"].includes(role);

  return (
    <div className="space-y-5">
      <Table
        columns={[
          { key: "type", label: "Type" },
          { key: "name", label: "Expert" },
          { key: "status", label: "Status" },
          { key: "cost", label: "Est. cost", align: "right" },
          { key: "actions", label: "" },
        ]}
        rows={assignments.map((a) => ({
          type: a.expert_type,
          name: a.expert_name,
          status: <StatusBadge status={a.status} />,
          cost: kes(a.estimated_cost ?? 0),
          actions: (
            <div className="flex justify-end gap-2">
              {(canAssign || (canUpdateOwn && a.expert_type === role) || (canUpdateOwn && role === "garage" && a.expert_type === "garage")) && (
                <>
                  {a.status === "pending" && (
                    <form
                      action={updateAssignmentStatusAction.bind(null, a.assignment_id, "accepted", claim.claim_ref, undefined)}
                    >
                      <button className="btn-ghost !px-2 !py-1 text-xs">Accept</button>
                    </form>
                  )}
                  {a.status === "accepted" && (
                    <form
                      action={updateAssignmentStatusAction.bind(null, a.assignment_id, "in_progress", claim.claim_ref, undefined)}
                    >
                      <button className="btn-ghost !px-2 !py-1 text-xs">Start</button>
                    </form>
                  )}
                  {(a.status === "accepted" || a.status === "in_progress") && (
                    <form
                      action={updateAssignmentStatusAction.bind(
                        null,
                        a.assignment_id,
                        "completed",
                        claim.claim_ref,
                        a.estimated_cost
                      )}
                    >
                      <button className="btn-ghost !px-2 !py-1 text-xs">Complete</button>
                    </form>
                  )}
                </>
              )}
            </div>
          ),
        }))}
        emptyLabel="No experts assigned yet."
      />

      {canAssign && (
        <form action={assignExpertAction} className="card space-y-3 p-4">
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <p className="text-sm font-bold">Assign an expert</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="field-label">Expert type</label>
              <select name="expert_type" className="field-input">
                <option value="assessor">Assessor</option>
                <option value="garage">Garage</option>
                <option value="investigator">Investigator</option>
                <option value="loss_adjuster">Loss Adjuster</option>
              </select>
            </div>
            <div>
              <label className="field-label">Name / company</label>
              <input name="expert_name" required className="field-input" />
            </div>
            <div>
              <label className="field-label">Phone</label>
              <input name="expert_phone" className="field-input" />
            </div>
            <div>
              <label className="field-label">Estimated cost (KES)</label>
              <input name="estimated_cost" type="number" min={0} className="field-input" />
            </div>
          </div>
          <div>
            <label className="field-label">Note</label>
            <textarea name="note" rows={2} className="field-input" />
          </div>
          <button className="btn-primary">Assign & Notify</button>
        </form>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------
const DOC_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "police_abstract", label: "Police abstract" },
  { value: "medical_report", label: "Medical report" },
  { value: "invoice", label: "Invoice / receipt" },
  { value: "surveyor_report", label: "Surveyor / assessor report" },
  { value: "demand_letter", label: "Demand letter" },
  { value: "id_document", label: "ID document" },
  { value: "photo", label: "Photo (damage / accident scene)" },
  { value: "discharge_voucher", label: "Discharge voucher" },
  { value: "engagement_letter", label: "Engagement letter" },
  { value: "consent_form", label: "Consent form" },
  { value: "other", label: "Other" },
];

function PhotoMetaSummary({ exifJson }: { exifJson: string | null }) {
  if (!exifJson) return null;
  try {
    const meta = JSON.parse(exifJson) as {
      captured_at: string | null;
      has_gps: boolean;
      days_from_loss: number | null;
      flags: string[];
    };
    const mismatch = meta.days_from_loss !== null && Math.abs(meta.days_from_loss) > 2;
    return (
      <div className="mt-1 space-y-0.5 text-[11px]">
        <p className={mismatch ? "font-semibold text-brand-red-dark" : "text-black/50"}>
          Captured: {meta.captured_at ? new Date(meta.captured_at).toLocaleString() : "unknown"}
          {" · "}GPS: {meta.has_gps ? "present" : "none"}
        </p>
        {meta.flags.map((f, i) => (
          <p key={i} className="text-brand-red-dark">
            ⚠ {f}
          </p>
        ))}
      </div>
    );
  } catch {
    return null;
  }
}

export function DocumentsPanel({
  claim,
  documents,
  canUpload,
}: {
  claim: Claim;
  documents: ClaimDocument[];
  canUpload: boolean;
}) {
  return (
    <div className="space-y-6">
      {canUpload && (
        <form
          action={uploadDocumentAction}
          className="grid gap-3 rounded-lg border border-dashed border-black/15 p-4 sm:grid-cols-4"
        >
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <div className="sm:col-span-1">
            <label className="field-label">Document type</label>
            <select name="doc_type" className="field-input" defaultValue="photo">
              {DOC_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="field-label">File</label>
            <input type="file" name="file" required className="field-input" />
          </div>
          <div className="flex items-end sm:col-span-1">
            <button className="btn-primary w-full">Upload &amp; scan</button>
          </div>
          <p className="text-xs text-black/45 sm:col-span-4">
            Images are OCR&apos;d automatically and, where present, their capture date/GPS metadata is
            extracted and cross-checked against the claimed loss date as a fraud-screening signal.
            Digital PDFs have their embedded text extracted; scanned/image-only PDFs are not OCR&apos;d in
            this demo.
          </p>
        </form>
      )}

      <Table
        columns={[
          { key: "type", label: "Type" },
          { key: "file", label: "Filename" },
          { key: "size", label: "Size", align: "right" },
          { key: "ocr", label: "OCR" },
          { key: "meta", label: "Photo metadata" },
          { key: "uploaded", label: "Uploaded" },
        ]}
        rows={documents.map((d) => ({
          type: <Badge tone="blue">{d.doc_type.replace(/_/g, " ")}</Badge>,
          file: d.filename,
          size: `${Math.round(d.file_size / 1024)} KB`,
          ocr: (
            <div>
              <StatusBadge status={d.ocr_status} />
              {d.ocr_text && (
                <p className="mt-1 max-w-xs truncate text-[11px] text-black/50" title={d.ocr_text}>
                  {d.ocr_text.slice(0, 80)}
                  {d.ocr_text.length > 80 ? "…" : ""}
                </p>
              )}
            </div>
          ),
          meta: <PhotoMetaSummary exifJson={d.exif_json} />,
          uploaded: `${fmt(d.uploaded_at)} · v${d.version}`,
        }))}
        emptyLabel="No documents uploaded yet."
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settlements
// ---------------------------------------------------------------------------
export function SettlementsPanel({
  claim,
  settlements,
  canRecommend,
  canApprove,
  canMarkPaid,
}: {
  claim: Claim;
  settlements: Settlement[];
  canRecommend: boolean;
  canApprove: boolean;
  canMarkPaid: boolean;
}) {
  return (
    <div className="space-y-5">
      <Table
        columns={[
          { key: "id", label: "Settlement" },
          { key: "payee", label: "Payee" },
          { key: "amount", label: "Gross", align: "right" },
          { key: "wht", label: "WHT", align: "right" },
          { key: "net", label: "Net Payable", align: "right" },
          { key: "status", label: "Status" },
          { key: "actions", label: "" },
        ]}
        rows={settlements.map((s) => ({
          id: <span className="font-mono text-xs">{s.settlement_id}</span>,
          payee: `${s.payee_name} (${s.payee_type})`,
          amount: kes(s.amount),
          wht: kes(s.wht_amount),
          net: <span className="font-semibold">{kes(s.net_amount)}</span>,
          status: <StatusBadge status={s.status} />,
          actions: (
            <div className="flex justify-end gap-2">
              {canApprove && s.status === "pending" && (
                <form action={approveSettlementAction.bind(null, s.settlement_id, claim.claim_ref)}>
                  <button className="btn-ghost !px-2 !py-1 text-xs">Approve</button>
                </form>
              )}
              {canMarkPaid && s.status === "approved" && (
                <form action={markSettlementPaidAction} className="flex items-center gap-1">
                  <input type="hidden" name="claim_ref" value={claim.claim_ref} />
                  <input type="hidden" name="settlement_id" value={s.settlement_id} />
                  <input
                    name="bank_ref"
                    placeholder="Bank ref"
                    className="field-input !py-1 !text-xs"
                    style={{ width: 110 }}
                    required
                  />
                  <button className="btn-ghost !px-2 !py-1 text-xs">Pay</button>
                </form>
              )}
            </div>
          ),
        }))}
        emptyLabel="No settlements recorded."
      />

      {canRecommend && (
        <form action={recommendSettlementAction} className="card space-y-3 p-4">
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <p className="text-sm font-bold">Recommend a settlement</p>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="field-label">Amount (KES)</label>
              <input name="amount" type="number" min={0} required className="field-input" />
            </div>
            <div>
              <label className="field-label">Payee name</label>
              <input name="payee_name" defaultValue={claim.insured_name} required className="field-input" />
            </div>
            <div>
              <label className="field-label">Payee type</label>
              <select name="payee_type" className="field-input">
                <option value="insured">Insured</option>
                <option value="garage">Garage</option>
                <option value="assessor">Assessor</option>
                <option value="investigator">Investigator</option>
                <option value="spare_parts">Spare Parts</option>
                <option value="third_party">Third Party</option>
              </select>
            </div>
          </div>
          <div>
            <label className="field-label">Note</label>
            <textarea name="note" rows={2} className="field-input" />
          </div>
          <button className="btn-primary">Submit for Approval</button>
        </form>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// RFQ / Bids
// ---------------------------------------------------------------------------
export function RfqPanel({
  claim,
  rfqs,
  bidsByRfq,
  canBid,
  canAward,
}: {
  claim: Claim;
  rfqs: Rfq[];
  bidsByRfq: Record<string, Bid[]>;
  canBid: boolean;
  canAward: boolean;
}) {
  if (rfqs.length === 0) {
    return <p className="text-sm text-black/40">No spare-parts RFQs on this claim.</p>;
  }
  return (
    <div className="space-y-6">
      {rfqs.map((rfq) => {
        const bids = bidsByRfq[rfq.rfq_ref] ?? [];
        return (
          <div key={rfq.rfq_ref} className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="font-mono text-xs text-black/40">{rfq.rfq_ref}</p>
                <p className="text-sm font-bold">
                  {rfq.part_description} × {rfq.quantity}
                </p>
              </div>
              <StatusBadge status={rfq.status} />
            </div>
            <Table
              columns={[
                { key: "provider", label: "Provider" },
                { key: "brand", label: "Brand / Condition" },
                { key: "price", label: "Unit price", align: "right" },
                { key: "lead", label: "Lead" },
                { key: "warranty", label: "Warranty" },
                { key: "rating", label: "Rating" },
                { key: "status", label: "" },
                ...(canAward && rfq.status === "open" ? [{ key: "actions", label: "" }] : []),
              ]}
              rows={bids.map((b) => ({
                provider: b.provider,
                brand: `${b.brand} — ${b.condition}`,
                price: kes(b.unit_price),
                lead: `${b.lead_days}d`,
                warranty: b.warranty,
                rating: `${b.rating}/5`,
                status: <StatusBadge status={b.status} />,
                actions: (
                  <form action={awardBidAction.bind(null, b.bid_ref, rfq.rfq_ref, claim.claim_ref)}>
                    <button className="btn-ghost !px-2 !py-1 text-xs">Award</button>
                  </form>
                ),
              }))}
              emptyLabel="No bids yet."
            />
            {canBid && rfq.status === "open" && (
              <form action={submitBidAction} className="mt-3 grid gap-2 sm:grid-cols-6">
                <input type="hidden" name="claim_ref" value={claim.claim_ref} />
                <input type="hidden" name="rfq_ref" value={rfq.rfq_ref} />
                <input name="provider" placeholder="Your company" required className="field-input sm:col-span-2" />
                <input name="brand" placeholder="Brand" required className="field-input" />
                <input name="condition" placeholder="Condition" required className="field-input" />
                <input name="unit_price" type="number" placeholder="Price" required className="field-input" />
                <input name="lead_days" type="number" placeholder="Lead days" required className="field-input" />
                <input name="warranty" placeholder="Warranty" className="field-input" />
                <input name="rating" type="number" step="0.1" min="1" max="5" placeholder="Rating" className="field-input" />
                <button className="btn-primary sm:col-span-2">Submit Bid</button>
              </form>
            )}
          </div>
        );
      })}
    </div>
  );
}
