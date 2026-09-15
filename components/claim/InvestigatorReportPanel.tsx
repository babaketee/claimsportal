import { Badge } from "@/components/ui/Badge";
import { fileInvestigatorReportAction } from "@/app/actions/claims";
import type { Claim, InvestigatorReport } from "@/lib/types";

export function InvestigatorReportPanel({
  claim,
  reports,
  canFile,
}: {
  claim: Claim;
  reports: InvestigatorReport[];
  canFile: boolean;
}) {
  return (
    <div className="card space-y-4 p-4">
      <div>
        <p className="text-sm font-bold text-brand-ink">Notification of Incident (Investigator)</p>
        <p className="mt-1 text-xs text-black/55">
          The 7th Definite Assurance claim form — filed by the assigned investigator, not the client.
          Its Fraud-Risk &amp; Report Log feeds directly into the fraud-screening engine.
        </p>
      </div>

      {reports.length > 0 && (
        <ul className="space-y-2">
          {reports.map((r) => (
            <li key={r.report_id} className="rounded-lg border border-black/10 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{r.investigator_name}</span>
                <Badge tone={r.fraud_suspected === "yes" ? "red" : "green"}>
                  Fraud suspected: {r.fraud_suspected}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-black/55">
                {r.location} · {r.accident_datetime ? new Date(r.accident_datetime).toLocaleString() : "—"} ·
                {" "}
                {new Date(r.created_at).toLocaleDateString()}
              </p>
              {r.fraud_basis && <p className="mt-1 text-xs text-black/70">{r.fraud_basis}</p>}
            </li>
          ))}
        </ul>
      )}

      {canFile && (
        <form action={fileInvestigatorReportAction} className="grid gap-3 border-t border-black/10 pt-4 sm:grid-cols-2">
          <input type="hidden" name="claim_ref" value={claim.claim_ref} />
          <div>
            <label className="field-label">Investigator name &amp; firm</label>
            <input name="investigator_name" required className="field-input" placeholder="e.g. Sentinel Risk Investigators" />
          </div>
          <div>
            <label className="field-label">Mode of report</label>
            <select name="mode_of_report" className="field-input" defaultValue="Telephone">
              <option>Telephone</option>
              <option>Walk-in</option>
              <option>Media</option>
              <option>Mobile App</option>
            </select>
          </div>
          <div>
            <label className="field-label">Date &amp; time of accident</label>
            <input name="accident_datetime" type="datetime-local" className="field-input" />
          </div>
          <div>
            <label className="field-label">Location of accident</label>
            <input name="location" className="field-input" defaultValue={claim.location} />
          </div>
          <div>
            <label className="field-label">Police station reported</label>
            <input name="police_station" className="field-input" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="field-label">Injured</label>
              <input name="injured_count" type="number" min={0} defaultValue={0} className="field-input" />
            </div>
            <div>
              <label className="field-label">Deceased</label>
              <input name="deceased_count" type="number" min={0} defaultValue={0} className="field-input" />
            </div>
          </div>
          <div className="sm:col-span-2 rounded-lg border border-amber-300 bg-amber-50 p-3">
            <label className="field-label">Suspected fraud indicators?</label>
            <select name="fraud_suspected" className="field-input" defaultValue="no">
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
            <label className="field-label mt-2">Basis / notes</label>
            <textarea name="fraud_basis" rows={2} className="field-input" placeholder="What raised the suspicion?" />
          </div>
          <div className="sm:col-span-2">
            <button className="btn-primary">File report</button>
          </div>
        </form>
      )}
    </div>
  );
}
