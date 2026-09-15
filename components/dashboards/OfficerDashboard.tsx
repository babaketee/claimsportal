import Link from "next/link";
import * as repo from "@/lib/repo";
import { SectionHeading } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { FilterBar } from "./FilterBar";
import { ClaimsTable } from "./ClaimsTable";
import { CLOSED_STATUSES } from "@/lib/types";

export function OfficerDashboard({
  email,
  status,
  category,
  q,
}: {
  email: string;
  status?: string;
  category?: string;
  q?: string;
}) {
  const allMine = repo.listClaims({ assigned_officer: email });
  const claims = repo.listClaims({ assigned_officer: email, status, category, q, limit: 100 });
  const overdue = repo.getOverdueEntries(email);
  const openCount = allMine.filter((c) => !CLOSED_STATUSES.includes(c.status)).length;
  const highUrgency = allMine.filter((c) => c.urgency === "High" && !CLOSED_STATUSES.includes(c.status)).length;
  const totalReserveExposure = allMine.reduce((s, c) => s + (CLOSED_STATUSES.includes(c.status) ? 0 : c.claim_amount), 0);

  return (
    <div>
      <SectionHeading title="Claims Officer Portal" subtitle="Your assigned claims, diary and workflows" />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Open claims" value={String(openCount)} tone="red" />
        <StatCard label="High urgency" value={String(highUrgency)} tone="red" />
        <StatCard label="Overdue diary" value={String(overdue.length)} tone="red" />
        <StatCard label="Open exposure" value={kes(totalReserveExposure)} />
      </div>

      {overdue.length > 0 && (
        <div className="mb-6 rounded-lg border border-brand-red/30 bg-brand-red-10 p-4">
          <p className="mb-2 text-sm font-bold text-brand-red-dark">⚠ {overdue.length} overdue diary entries</p>
          <ul className="space-y-1 text-sm text-brand-red-dark/90">
            {overdue.slice(0, 5).map((d) => (
              <li key={d.entry_id}>
                <Link href={`/app/claims/${d.claim_ref}`} className="underline">
                  {d.claim_ref}
                </Link>{" "}
                — {d.task} (due {d.due_date})
              </li>
            ))}
          </ul>
        </div>
      )}

      <FilterBar basePath="/app" status={status} category={category} q={q} />
      <ClaimsTable claims={claims} emptyLabel="No claims match this filter." />
    </div>
  );
}
