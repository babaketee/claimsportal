import Link from "next/link";
import * as repo from "@/lib/repo";
import { SectionHeading, Card } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { StatusBarChart, CategoryPieChart } from "@/components/charts/Charts";
import { Table } from "@/components/ui/Table";
import { CLOSED_STATUSES } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { approveReserveAction, approveSettlementAction } from "@/app/actions/claims";

export function HeadOfClaimsDashboard() {
  const summary = repo.claimsSummary();
  const byStatus = repo.countClaimsByStatus();
  const pendingReserves = repo.getPendingReserves();
  const pendingSettlements = repo.getSettlementsByStatus("pending");
  const fraudQueue = repo.getFraudQueue();
  const allClaims = repo.listClaims({ limit: 500 });
  const slaBreaches = allClaims.filter(
    (c) => !CLOSED_STATUSES.includes(c.status) && repo.getSlaStatus(c.date_reported).settlement_overdue
  );

  const motorCount = allClaims.filter((c) => c.category === "Motor").length;
  const businessCount = allClaims.filter((c) => c.category === "Business").length;

  return (
    <div>
      <SectionHeading title="Head of Claims — Oversight" subtitle="Portfolio health, approvals and SLA exposure" />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Total claims" value={String(summary.total)} />
        <StatCard label="Open" value={String(summary.open)} tone="red" />
        <StatCard label="Open exposure" value={kes(summary.totalExposure)} />
        <StatCard label="Settled value" value={kes(summary.settledValue)} />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <Card title="Claims by status">
          <StatusBarChart data={byStatus.map((s) => ({ status: s.status, n: s.n }))} />
        </Card>
        <Card title="Motor vs Business">
          <CategoryPieChart
            data={[
              { name: "Motor", value: motorCount },
              { name: "Business", value: businessCount },
            ]}
          />
        </Card>
      </div>

      {slaBreaches.length > 0 && (
        <div className="mb-8 rounded-lg border border-brand-red/30 bg-brand-red-10 p-4">
          <p className="mb-2 text-sm font-bold text-brand-red-dark">
            ⚠ {slaBreaches.length} claims past the 30-day settlement SLA
          </p>
          <ul className="grid gap-1 text-sm text-brand-red-dark/90 sm:grid-cols-2">
            {slaBreaches.slice(0, 10).map((c) => (
              <li key={c.claim_ref}>
                <Link href={`/app/claims/${c.claim_ref}`} className="underline">
                  {c.claim_ref}
                </Link>{" "}
                — {c.insured_name} ({c.status})
              </li>
            ))}
          </ul>
        </div>
      )}

      {fraudQueue.length > 0 && (
        <div className="mb-8">
          <h3 className="mb-3 text-sm font-bold">Fraud screening — pending human review ({fraudQueue.length})</h3>
          <Table
            columns={[
              { key: "ref", label: "Claim" },
              { key: "score", label: "Score", align: "right" },
              { key: "band", label: "Risk band" },
              { key: "action", label: "Recommended action" },
            ]}
            rows={fraudQueue.slice(0, 15).map((f) => ({
              ref: (
                <Link href={`/app/claims/${f.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
                  {f.claim_ref}
                </Link>
              ),
              score: f.score,
              band: (
                <Badge tone={f.risk_band === "High" ? "red" : f.risk_band === "Medium" ? "amber" : "green"}>
                  {f.risk_band}
                </Badge>
              ),
              action: <span className="text-xs text-black/60">{f.recommended_action}</span>,
            }))}
            emptyLabel="No claims awaiting fraud review."
          />
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-bold">Reserve approvals pending ({pendingReserves.length})</h3>
          <Table
            columns={[
              { key: "ref", label: "Claim" },
              { key: "amount", label: "Amount", align: "right" },
              { key: "purpose", label: "Purpose" },
              { key: "action", label: "" },
            ]}
            rows={pendingReserves.slice(0, 15).map((r) => ({
              ref: (
                <Link href={`/app/claims/${r.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
                  {r.claim_ref}
                </Link>
              ),
              amount: kes(r.amount),
              purpose: r.purpose,
              action: (
                <form action={approveReserveAction.bind(null, r.reserve_id, r.claim_ref)}>
                  <button className="btn-ghost !px-2 !py-1 text-xs">Approve</button>
                </form>
              ),
            }))}
            emptyLabel="No reserves awaiting approval."
          />
        </div>
        <div>
          <h3 className="mb-3 text-sm font-bold">Settlements pending approval ({pendingSettlements.length})</h3>
          <Table
            columns={[
              { key: "ref", label: "Claim" },
              { key: "payee", label: "Payee" },
              { key: "amount", label: "Net", align: "right" },
              { key: "action", label: "" },
            ]}
            rows={pendingSettlements.slice(0, 15).map((s) => ({
              ref: s.claim ? (
                <Link href={`/app/claims/${s.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
                  {s.claim_ref}
                </Link>
              ) : (
                s.claim_ref
              ),
              payee: `${s.payee_name} (${s.payee_type})`,
              amount: kes(s.net_amount),
              action: (
                <form action={approveSettlementAction.bind(null, s.settlement_id, s.claim_ref)}>
                  <button className="btn-ghost !px-2 !py-1 text-xs">Approve</button>
                </form>
              ),
            }))}
            emptyLabel="No settlements awaiting approval."
          />
        </div>
      </div>
    </div>
  );
}
