import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import * as repo from "@/lib/repo";
import { ensureDefaultConfigs, CONFIG_LABELS } from "@/lib/config";
import { SectionHeading, Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { proposeConfigAction, approveConfigAction, rejectConfigAction } from "@/app/actions/claims";

export default async function ConfigAdminPage() {
  const session = await getSession();
  if (!["admin", "super_admin"].includes(session.role)) redirect("/app");

  ensureDefaultConfigs();

  const active = repo.getAllActiveConfigs();
  const pending = repo.getPendingConfigs();

  return (
    <div>
      <SectionHeading
        title="Configuration Engine"
        subtitle="Versioned, effective-dated settings changed only through a maker-checker approval flow (design doc section 10)"
      />

      {pending.length > 0 && (
        <div className="mb-8">
          <h3 className="mb-3 text-sm font-bold">Pending approval ({pending.length})</h3>
          <div className="space-y-3">
            {pending.map((p) => (
              <div key={`${p.config_key}-${p.version}`} className="card space-y-2 p-4">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-brand-ink">
                    {CONFIG_LABELS[p.config_key] ?? p.config_key} — v{p.version}
                  </p>
                  <StatusBadge status={p.status} />
                </div>
                <pre className="overflow-x-auto rounded-lg bg-black/5 p-3 text-xs">{p.value_json}</pre>
                <p className="text-xs text-black/45">
                  Proposed by {p.proposed_by} on {new Date(p.proposed_at).toLocaleString()}
                  {p.note ? ` — ${p.note}` : ""}
                </p>
                <div className="flex gap-2">
                  <form action={approveConfigAction.bind(null, p.config_key, p.version)}>
                    <button className="btn-primary text-xs">
                      Approve (as {session.email === p.proposed_by ? "—cannot self-approve—" : session.email})
                    </button>
                  </form>
                  <form action={rejectConfigAction.bind(null, p.config_key, p.version)}>
                    <button className="btn-ghost text-xs">Reject</button>
                  </form>
                </div>
                {session.email === p.proposed_by && (
                  <p className="text-xs font-medium text-brand-red-dark">
                    Maker-checker: sign in as a different administrator to approve your own proposal.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <h3 className="mb-3 text-sm font-bold">Active configuration</h3>
      <div className="grid gap-4 md:grid-cols-2">
        {active.map((c) => (
          <Card key={c.config_key} title={CONFIG_LABELS[c.config_key] ?? c.config_key}>
            <pre className="mb-3 overflow-x-auto rounded-lg bg-black/5 p-3 text-xs">{c.value_json}</pre>
            <p className="mb-3 text-xs text-black/45">
              v{c.version} · approved by {c.approved_by} on{" "}
              {c.approved_at ? new Date(c.approved_at).toLocaleDateString() : "—"}
            </p>
            <form action={proposeConfigAction} className="space-y-2">
              <input type="hidden" name="config_key" value={c.config_key} />
              <label className="field-label">Propose new value (JSON)</label>
              <textarea
                name="value_json"
                rows={3}
                className="field-input font-mono text-xs"
                defaultValue={c.value_json}
              />
              <input name="note" placeholder="Reason for change" className="field-input" />
              <button className="btn-secondary text-xs">Propose change (maker)</button>
            </form>
          </Card>
        ))}
      </div>
    </div>
  );
}
