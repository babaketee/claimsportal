import Link from "next/link";
import * as repo from "@/lib/repo";
import { isDocusealConfigured } from "@/lib/docuseal";
import { DEMO_ACCOUNTS } from "@/lib/accounts";
import { FORM_DEFINITIONS } from "@/lib/claim-forms";
import { DOCUSEAL_WORKFLOW_LABELS, ROLE_LABELS, type DocusealWorkflow } from "@/lib/types";
import { SectionHeading, Card } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { Badge } from "@/components/ui/Badge";
import { StatusBarChart, ClaimTypeBarChart } from "@/components/charts/Charts";
import { Table } from "@/components/ui/Table";

const SIMPLE_WORKFLOWS: DocusealWorkflow[] = ["settlement_discharge", "demand_letter", "engagement_letter"];

export function SuperAdminDashboard() {
  const summary = repo.claimsSummary();
  const byStatus = repo.countClaimsByStatus();
  const byType = repo.countClaimsByType();
  const users = Object.entries(DEMO_ACCOUNTS);

  return (
    <div>
      <SectionHeading
        title="Super Admin — System Configuration"
        subtitle="Platform-wide visibility & integrations"
        action={
          <Link href="/app/admin/config" className="btn-secondary text-xs">
            Configuration Engine →
          </Link>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Total claims" value={String(summary.total)} />
        <StatCard label="Total exposure" value={kes(summary.totalExposure)} />
        <StatCard label="Settled value" value={kes(summary.settledValue)} />
        <StatCard label="User accounts" value={String(users.length)} />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <Card title="Claims by status">
          <StatusBarChart data={byStatus.map((s) => ({ status: s.status, n: s.n }))} />
        </Card>
        <Card title="Claims by type">
          <ClaimTypeBarChart data={byType} />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="DocuSeal e-signature configuration">
          <p className="mb-3 text-xs text-black/50">
            Set DOCUSEAL_HOST / DOCUSEAL_API_KEY / template ids in .env.local to go live per
            workflow. Each of the 7 uploaded claim forms has its own claim_form template id.
          </p>
          <Table
            columns={[
              { key: "workflow", label: "Workflow" },
              { key: "status", label: "Status" },
            ]}
            rows={[
              ...SIMPLE_WORKFLOWS.map((w) => ({
                workflow: DOCUSEAL_WORKFLOW_LABELS[w],
                status: isDocusealConfigured(w) ? (
                  <Badge tone="green">Configured</Badge>
                ) : (
                  <Badge tone="amber">Demo mode</Badge>
                ),
              })),
              ...Object.values(FORM_DEFINITIONS).map((f) => ({
                workflow: `Claim form: ${f.title}`,
                status: isDocusealConfigured("claim_form", f.key) ? (
                  <Badge tone="green">Configured</Badge>
                ) : (
                  <Badge tone="amber">Demo mode</Badge>
                ),
              })),
            ]}
          />
        </Card>
        <Card title="Role → access matrix">
          <Table
            columns={[
              { key: "role", label: "Role" },
              { key: "email", label: "Demo login" },
            ]}
            rows={users.map(([email, a]) => ({
              role: ROLE_LABELS[a.role],
              email: <span className="font-mono text-xs">{email}</span>,
            }))}
          />
        </Card>
      </div>
    </div>
  );
}
