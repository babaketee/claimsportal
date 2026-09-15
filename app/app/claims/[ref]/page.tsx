import Link from "next/link";
import { notFound } from "next/navigation";
import { getSession } from "@/lib/session";
import * as repo from "@/lib/repo";
import { isDocusealConfigured } from "@/lib/docuseal";
import { formDefinitionFor, formKeyForClaimType } from "@/lib/claim-forms";
import { stageForStatus, stageNameForStatus, LIFECYCLE_STAGES } from "@/lib/types";
import { StatusBadge, UrgencyBadge } from "@/components/ui/Badge";
import { SectionHeading } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { kes } from "@/components/ui/Stat";
import { DocusealPanel } from "@/components/DocusealPanel";
import { FraudPanel } from "@/components/claim/FraudPanel";
import { InvestigatorReportPanel } from "@/components/claim/InvestigatorReportPanel";
import {
  ReservesPanel,
  DiaryPanel,
  CommsPanel,
  AssignmentsPanel,
  DocumentsPanel,
  SettlementsPanel,
  RfqPanel,
} from "@/components/claim/panels";

export default async function ClaimDetailPage({ params }: { params: { ref: string } }) {
  const session = await getSession();
  const claim = repo.getClaim(params.ref);
  if (!claim) notFound();

  const role = session.role;
  const isStaff = role !== "client";
  if (role === "client" && claim.client_email !== session.email) {
    // Clients may only view their own claims.
    notFound();
  }

  const reserves = repo.getReserves(claim.claim_ref);
  const diary = repo.getDiaryEntries(claim.claim_ref);
  const comms = repo.getCommunications(claim.claim_ref);
  const assignments = repo.getAssignments(claim.claim_ref);
  const documents = repo.getDocuments(claim.claim_ref);
  const settlements = repo.getSettlements(claim.claim_ref);
  const rfqs = repo.getRfqsForClaim(claim.claim_ref);
  const bidsByRfq = Object.fromEntries(rfqs.map((r) => [r.rfq_ref, repo.getBids(r.rfq_ref)]));
  const sla = repo.getSlaStatus(claim.date_reported);
  const docusealAll = repo.getDocusealSubmissions(claim.claim_ref);
  const docusealFor = (w: string) => docusealAll.filter((d) => d.workflow === w);
  const fraudAssessments = repo.getFraudAssessments(claim.claim_ref);
  const statusHistory = repo.getStatusHistory(claim.claim_ref);
  const investigatorReports = repo.getInvestigatorReports(claim.claim_ref);
  const claimFormKey = formKeyForClaimType(claim.claim_type);
  const claimFormDef = formDefinitionFor(claim.claim_type);

  const canManageOps = ["claims_officer", "admin", "super_admin"].includes(role);
  const canApproveSettlement = ["head_of_claims", "admin", "super_admin"].includes(role);
  const canMarkPaid = ["finance", "finance_head", "admin", "super_admin"].includes(role);
  const canDoLegal = ["legal", "admin", "super_admin"].includes(role);
  const canBidOnRfq = role === "spare_parts";
  const canAwardBid = canManageOps;
  const canReviewFraud = ["head_of_claims", "claims_officer", "admin", "super_admin"].includes(role);
  const isInvestigator = role === "investigator";

  const tabs = [
    {
      label: "Overview",
      content: (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="card space-y-2 p-4 md:col-span-2">
            <Row label="Insured / Client" value={claim.insured_name} />
            <Row label="Policy number" value={claim.policy_number} />
            {claim.vehicle_reg && <Row label="Vehicle" value={claim.vehicle_reg} />}
            <Row label="Location" value={claim.location} />
            <Row label="Date reported" value={claim.date_reported} />
            <Row label="Claim type" value={claim.claim_type} />
            <Row label="Description" value={claim.description} />
            <Row label="Assigned officer" value={claim.assigned_officer ?? "Unassigned"} />
          </div>
          <div className="space-y-4">
            <div className="card p-4">
              <p className="text-xs font-semibold uppercase text-black/45">Claim amount</p>
              <p className="mt-1 text-2xl font-extrabold text-brand-green">{kes(claim.claim_amount)}</p>
            </div>
            <div className="card space-y-2 p-4">
              <p className="text-xs font-semibold uppercase text-black/45">SLA</p>
              <Row
                label="Acknowledgement"
                value={sla.acknowledged_overdue ? "Overdue" : `${sla.days_to_ack}d left`}
                warn={sla.acknowledged_overdue}
              />
              <Row
                label="Settlement"
                value={sla.settlement_overdue ? "Overdue" : `${sla.days_to_settle}d left`}
                warn={sla.settlement_overdue}
              />
            </div>
          </div>
        </div>
      ),
    },
    {
      label: "Lifecycle",
      content: (
        <div className="space-y-6">
          <div className="card p-4">
            <p className="mb-3 text-xs font-bold uppercase text-black/45">
              10-stage claim lifecycle — currently at Stage {stageForStatus(claim.status)}:{" "}
              {stageNameForStatus(claim.status)}
            </p>
            <ol className="grid gap-2 sm:grid-cols-2">
              {LIFECYCLE_STAGES.map((s) => {
                const current = s.stage === stageForStatus(claim.status);
                const past = s.stage < stageForStatus(claim.status);
                return (
                  <li
                    key={s.stage}
                    className={`rounded-lg border p-2 text-xs ${
                      current
                        ? "border-brand-green bg-brand-green-10 font-bold text-brand-green"
                        : past
                          ? "border-black/10 text-black/45 line-through"
                          : "border-black/10 text-black/60"
                    }`}
                  >
                    Stage {s.stage}: {s.name}
                  </li>
                );
              })}
            </ol>
          </div>
          <div className="card p-4">
            <p className="mb-3 text-xs font-bold uppercase text-black/45">
              Status history (immutable audit trail)
            </p>
            <ul className="space-y-2 text-sm">
              {statusHistory.length === 0 && <li className="text-black/45">No status changes recorded yet.</li>}
              {statusHistory.map((h) => (
                <li key={h.history_id} className="border-b border-black/5 pb-2 last:border-0">
                  <span className="font-medium text-brand-ink">
                    {h.from_status ?? "—"} → {h.to_status}
                  </span>
                  <span className="ml-2 text-xs text-black/45">
                    {new Date(h.changed_at).toLocaleString()} · {h.changed_by}
                  </span>
                  {h.note && <p className="text-xs text-black/55">{h.note}</p>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ),
    },
    { label: "Reserves", content: <ReservesPanel claim={claim} reserves={reserves} canManage={canManageOps} /> },
    {
      label: "Assignments",
      content: (
        <AssignmentsPanel claim={claim} assignments={assignments} canAssign={canManageOps} role={role} />
      ),
    },
    {
      label: "Diary & Correspondence",
      content: (
        <div className="space-y-8">
          <DiaryPanel claim={claim} diary={diary} canManage={canManageOps || canDoLegal} />
          <div>
            <h4 className="mb-3 text-sm font-bold">Communications log</h4>
            <CommsPanel claim={claim} comms={comms} canManage={canManageOps || canDoLegal} />
          </div>
        </div>
      ),
    },
    {
      label: "Documents",
      content: <DocumentsPanel claim={claim} documents={documents} canUpload={isStaff || role === "client"} />,
    },
    {
      label: "Fraud & Risk",
      content: (
        <div className="space-y-6">
          <FraudPanel
            claim={claim}
            assessments={fraudAssessments}
            canReview={canReviewFraud}
            canRerun={canManageOps}
          />
          {(isInvestigator || canManageOps) && (
            <InvestigatorReportPanel claim={claim} reports={investigatorReports} canFile={isInvestigator || canManageOps} />
          )}
        </div>
      ),
    },
    {
      label: "Settlements",
      content: (
        <SettlementsPanel
          claim={claim}
          settlements={settlements}
          canRecommend={canManageOps}
          canApprove={canApproveSettlement}
          canMarkPaid={canMarkPaid}
        />
      ),
    },
    ...(rfqs.length > 0 || role === "spare_parts"
      ? [
          {
            label: "Spare Parts RFQ",
            content: (
              <RfqPanel
                claim={claim}
                rfqs={rfqs}
                bidsByRfq={bidsByRfq}
                canBid={canBidOnRfq}
                canAward={canAwardBid}
              />
            ),
          },
        ]
      : []),
    {
      label: "E-Signatures",
      content: (
        <div className="space-y-6">
          {(role === "client" || isStaff) && (
            <DocusealPanel
              claimRef={claim.claim_ref}
              workflow="claim_form"
              formKey={claimFormKey}
              formDefinition={claimFormDef}
              configured={isDocusealConfigured("claim_form", claimFormKey)}
              submissions={docusealFor("claim_form")}
              defaultSignerName={claim.insured_name}
              defaultSignerEmail={claim.client_email ?? "client@insure.demo"}
              description={`${claimFormDef.title} — declaration and DPA 2019 consent for processing this claim.`}
            />
          )}
          {(canDoLegal || role === "client") && (
            <DocusealPanel
              claimRef={claim.claim_ref}
              workflow="demand_letter"
              configured={isDocusealConfigured("demand_letter")}
              submissions={docusealFor("demand_letter")}
              defaultSignerName={claim.insured_name}
              defaultSignerEmail={claim.client_email ?? "client@insure.demo"}
              description="Demand letter or repudiation notice requiring claimant countersignature/acknowledgement."
            />
          )}
          {(canMarkPaid || canManageOps || role === "client") && (
            <DocusealPanel
              claimRef={claim.claim_ref}
              workflow="settlement_discharge"
              configured={isDocusealConfigured("settlement_discharge")}
              submissions={docusealFor("settlement_discharge")}
              defaultSignerName={claim.insured_name}
              defaultSignerEmail={claim.client_email ?? "client@insure.demo"}
              description="Discharge voucher signed by the claimant before final settlement payment is released."
            />
          )}
          {(["assessor", "garage", "investigator"].includes(role) || canManageOps) && (
            <DocusealPanel
              claimRef={claim.claim_ref}
              workflow="engagement_letter"
              configured={isDocusealConfigured("engagement_letter")}
              submissions={docusealFor("engagement_letter")}
              defaultSignerName={assignments[0]?.expert_name ?? "Service Provider"}
              defaultSignerEmail="provider@services.demo"
              description="Engagement/authorisation letter signed by the assigned assessor, garage or investigator."
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <Link href="/app" className="mb-4 inline-block text-sm font-medium text-brand-green hover:underline">
        ← Back to dashboard
      </Link>
      <SectionHeading
        title={claim.claim_ref}
        subtitle={`${claim.category} · ${claim.claim_type}`}
        action={
          <div className="flex gap-2">
            <StatusBadge status={claim.status} />
            <UrgencyBadge urgency={claim.urgency} />
          </div>
        }
      />
      <Tabs tabs={tabs} />
    </div>
  );
}

function Row({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-black/5 py-1.5 text-sm last:border-0">
      <span className="text-black/45">{label}</span>
      <span className={`text-right font-medium ${warn ? "text-brand-red" : "text-brand-ink"}`}>{value}</span>
    </div>
  );
}
