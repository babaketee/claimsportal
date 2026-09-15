import Link from "next/link";
import * as repo from "@/lib/repo";
import { SectionHeading } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/Stat";
import { StatusBadge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { ClaimsTable } from "./ClaimsTable";

export function LegalDashboard() {
  const repudiated = repo.listClaims({ status: "Repudiated" });
  const investigations = repo.listClaims({ status: "Under investigation and assessment" });
  const demandLetters = repo.getDocusealByWorkflow("demand_letter");
  const signed = demandLetters.filter((d) => d.status === "completed");

  return (
    <div>
      <SectionHeading title="Legal Counsel" subtitle="Repudiations, demand letters and litigation flags" />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Repudiated claims" value={String(repudiated.length)} tone="red" />
        <StatCard label="Under investigation" value={String(investigations.length)} />
        <StatCard label="Demand letters sent" value={String(demandLetters.length)} />
        <StatCard label="Countersigned" value={String(signed.length)} />
      </div>

      <h3 className="mb-3 text-sm font-bold">Repudiated claims — demand letter tracking</h3>
      <ClaimsTable claims={repudiated} emptyLabel="No repudiated claims." />

      <h3 className="mb-3 mt-8 text-sm font-bold">Demand letter e-signature status</h3>
      <Table
        columns={[
          { key: "ref", label: "Claim" },
          { key: "signer", label: "Signer" },
          { key: "status", label: "Status" },
          { key: "sent", label: "Sent" },
        ]}
        rows={demandLetters.map((d) => ({
          ref: (
            <Link href={`/app/claims/${d.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
              {d.claim_ref}
            </Link>
          ),
          signer: d.signer_name,
          status: <StatusBadge status={d.status} />,
          sent: new Date(d.created_at).toLocaleDateString(),
        }))}
        emptyLabel="No demand letters sent yet."
      />

      <h3 className="mb-3 mt-8 text-sm font-bold">Claims under investigation</h3>
      <ClaimsTable claims={investigations} emptyLabel="No claims currently under investigation." />
    </div>
  );
}
