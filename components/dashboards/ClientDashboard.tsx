import * as repo from "@/lib/repo";
import { SectionHeading, Card } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { ClaimsTable } from "./ClaimsTable";
import { fileNewClaimAction } from "@/app/actions/claims";
import { CLOSED_STATUSES } from "@/lib/types";

export function ClientDashboard({ email, fullName }: { email: string; fullName: string }) {
  const claims = repo.listClaims({ client_email: email });
  const open = claims.filter((c) => !CLOSED_STATUSES.includes(c.status)).length;
  const settled = claims.filter((c) => c.status === "Paid" || c.status === "Closed").length;
  const totalClaimed = claims.reduce((s, c) => s + c.claim_amount, 0);

  return (
    <div>
      <SectionHeading title={`Welcome back, ${fullName.split(" ")[0]}`} subtitle="Your policy & claims overview" />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Total claims" value={String(claims.length)} />
        <StatCard label="In progress" value={String(open)} tone="red" />
        <StatCard label="Settled" value={String(settled)} />
        <StatCard label="Total claimed" value={kes(totalClaimed)} tone="neutral" />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h3 className="mb-3 text-sm font-bold">My claims</h3>
          <ClaimsTable claims={claims} emptyLabel="You have no claims on file yet — file one on the right." />
        </div>
        <Card title="Report a new claim (FNOL)">
          <form action={fileNewClaimAction} className="space-y-3">
            <div>
              <label className="field-label">Category</label>
              <select name="category" className="field-input">
                <option value="Motor">Motor</option>
                <option value="Business">Business</option>
              </select>
            </div>
            <div>
              <label className="field-label">Claim type</label>
              <input name="claim_type" required placeholder="e.g. Windscreen" className="field-input" />
            </div>
            <div>
              <label className="field-label">Policy number</label>
              <input name="policy_number" placeholder="MOT/2026/xxxxx" className="field-input" />
            </div>
            <div>
              <label className="field-label">Vehicle reg (if motor)</label>
              <input name="vehicle_reg" placeholder="KDA 123A" className="field-input" />
            </div>
            <div>
              <label className="field-label">Date of loss / accident</label>
              <input name="date_of_loss" type="date" required className="field-input" />
            </div>
            <div>
              <label className="field-label">Location</label>
              <input name="location" required placeholder="e.g. Westlands, Nairobi" className="field-input" />
            </div>
            <div>
              <label className="field-label">Estimated amount (KES)</label>
              <input name="claim_amount" type="number" min={0} className="field-input" />
            </div>
            <div>
              <label className="field-label">What happened?</label>
              <textarea name="description" required rows={3} className="field-input" />
            </div>
            <button className="btn-primary w-full">Submit Claim</button>
          </form>
        </Card>
      </div>
    </div>
  );
}
