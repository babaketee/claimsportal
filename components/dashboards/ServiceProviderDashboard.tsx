import Link from "next/link";
import * as repo from "@/lib/repo";
import { SectionHeading } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { StatusBadge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { ROLE_LABELS } from "@/lib/types";
import type { Role } from "@/lib/types";
import { updateAssignmentStatusAction } from "@/app/actions/claims";

const TITLES: Record<string, string> = {
  assessor: "Assessor Workbench",
  garage: "Garage / Repairer Workbench",
  investigator: "Investigator Workbench",
};

export function ServiceProviderDashboard({ role }: { role: Role }) {
  const expertType = role as "assessor" | "garage" | "investigator";
  const assignments = repo.getAssignmentsByType(expertType);
  const pending = assignments.filter((a) => a.status === "pending");
  const active = assignments.filter((a) => a.status === "accepted" || a.status === "in_progress");
  const completed = assignments.filter((a) => a.status === "completed");
  const totalEarnings = completed.reduce((s, a) => s + (a.actual_cost ?? a.estimated_cost ?? 0), 0);

  return (
    <div>
      <SectionHeading
        title={TITLES[role] ?? ROLE_LABELS[role]}
        subtitle="Assignments routed to you across all claims"
      />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="New requests" value={String(pending.length)} tone="red" />
        <StatCard label="In progress" value={String(active.length)} />
        <StatCard label="Completed" value={String(completed.length)} />
        <StatCard label="Completed value" value={kes(totalEarnings)} />
      </div>

      <Table
        columns={[
          { key: "ref", label: "Claim" },
          { key: "insured", label: "Insured" },
          { key: "type", label: "Claim type" },
          { key: "cost", label: "Est. cost", align: "right" },
          { key: "status", label: "Status" },
          { key: "actions", label: "" },
        ]}
        rows={assignments.map((a) => ({
          ref: (
            <Link href={`/app/claims/${a.claim_ref}`} className="font-mono text-xs font-semibold text-brand-green hover:underline">
              {a.claim_ref}
            </Link>
          ),
          insured: a.claim?.insured_name ?? "—",
          type: a.claim?.claim_type ?? "—",
          cost: kes(a.estimated_cost ?? 0),
          status: <StatusBadge status={a.status} />,
          actions: (
            <div className="flex justify-end gap-2">
              {a.status === "pending" && (
                <form action={updateAssignmentStatusAction.bind(null, a.assignment_id, "accepted", a.claim_ref, undefined)}>
                  <button className="btn-ghost !px-2 !py-1 text-xs">Accept</button>
                </form>
              )}
              {a.status === "accepted" && (
                <form action={updateAssignmentStatusAction.bind(null, a.assignment_id, "in_progress", a.claim_ref, undefined)}>
                  <button className="btn-ghost !px-2 !py-1 text-xs">Start</button>
                </form>
              )}
              {(a.status === "accepted" || a.status === "in_progress") && (
                <form
                  action={updateAssignmentStatusAction.bind(
                    null,
                    a.assignment_id,
                    "completed",
                    a.claim_ref,
                    a.estimated_cost
                  )}
                >
                  <button className="btn-ghost !px-2 !py-1 text-xs">Complete</button>
                </form>
              )}
            </div>
          ),
        }))}
        emptyLabel="No assignments yet."
      />
    </div>
  );
}
