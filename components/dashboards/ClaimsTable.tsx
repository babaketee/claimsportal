import Link from "next/link";
import { Table } from "@/components/ui/Table";
import { StatusBadge, UrgencyBadge } from "@/components/ui/Badge";
import { kes } from "@/components/ui/Stat";
import type { Claim } from "@/lib/types";

export function ClaimsTable({ claims, emptyLabel }: { claims: Claim[]; emptyLabel?: string }) {
  return (
    <Table
      columns={[
        { key: "ref", label: "Claim Ref" },
        { key: "insured", label: "Insured / Client" },
        { key: "type", label: "Type" },
        { key: "reported", label: "Reported" },
        { key: "amount", label: "Amount", align: "right" },
        { key: "urgency", label: "Urgency" },
        { key: "status", label: "Status" },
      ]}
      rows={claims.map((c) => ({
        ref: (
          <Link href={`/app/claims/${c.claim_ref}`} className="font-mono text-xs font-semibold text-brand-green hover:underline">
            {c.claim_ref}
          </Link>
        ),
        insured: (
          <div>
            <p className="font-medium">{c.insured_name}</p>
            {c.vehicle_reg && <p className="text-xs text-black/40">{c.vehicle_reg}</p>}
          </div>
        ),
        type: c.claim_type,
        reported: c.date_reported,
        amount: kes(c.claim_amount),
        urgency: <UrgencyBadge urgency={c.urgency} />,
        status: <StatusBadge status={c.status} />,
      }))}
      emptyLabel={emptyLabel}
    />
  );
}
