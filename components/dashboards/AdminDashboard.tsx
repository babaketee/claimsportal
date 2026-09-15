import Link from "next/link";
import * as repo from "@/lib/repo";
import { DEMO_ACCOUNTS } from "@/lib/accounts";
import { ROLE_LABELS } from "@/lib/types";
import { SectionHeading, Card } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/Stat";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";

export function AdminDashboard() {
  const summary = repo.claimsSummary();
  const byType = repo.countClaimsByType();
  const users = Object.entries(DEMO_ACCOUNTS);

  return (
    <div>
      <SectionHeading
        title="Internal Staff / Admin"
        subtitle="Accounts, document activity and portfolio mix"
        action={
          <Link href="/app/admin/config" className="btn-secondary text-xs">
            Configuration Engine →
          </Link>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Total claims" value={String(summary.total)} />
        <StatCard label="Open" value={String(summary.open)} tone="red" />
        <StatCard label="Settled" value={String(summary.settled)} />
        <StatCard label="Demo accounts" value={String(users.length)} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Demo accounts">
          <Table
            columns={[
              { key: "email", label: "Email" },
              { key: "role", label: "Role" },
              { key: "name", label: "Name" },
            ]}
            rows={users.map(([email, a]) => ({
              email: <span className="font-mono text-xs">{email}</span>,
              role: <Badge tone="green">{ROLE_LABELS[a.role]}</Badge>,
              name: a.full_name,
            }))}
          />
        </Card>
        <Card title="Claims by type">
          <Table
            columns={[
              { key: "type", label: "Claim type" },
              { key: "n", label: "Count", align: "right" },
            ]}
            rows={byType.map((t) => ({ type: t.claim_type, n: String(t.n) }))}
          />
        </Card>
      </div>
    </div>
  );
}
