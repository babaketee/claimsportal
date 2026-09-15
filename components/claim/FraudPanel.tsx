"use client";

import { useTransition } from "react";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { runFraudAssessmentAction, reviewFraudAssessmentAction } from "@/app/actions/claims";
import type { Claim, FraudAssessment, FraudIndicator } from "@/lib/types";

function bandTone(band: string): "green" | "amber" | "red" {
  if (band === "High") return "red";
  if (band === "Medium") return "amber";
  return "green";
}

export function FraudPanel({
  claim,
  assessments,
  canReview,
  canRerun,
}: {
  claim: Claim;
  assessments: FraudAssessment[];
  canReview: boolean;
  canRerun: boolean;
}) {
  const [pending, startTransition] = useTransition();
  const latest = assessments[0];
  const indicators: FraudIndicator[] = latest ? JSON.parse(latest.indicators_json) : [];

  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-brand-green-10/50 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-brand-green">AI-Assisted Fraud Screening &amp; Triage</p>
            <p className="mt-1 text-xs text-black/55">
              A deterministic, explainable rules engine that scores and routes claims — it never
              approves or declines a claim; a human always makes that call.
            </p>
          </div>
          {canRerun && (
            <button
              className="btn-ghost text-xs"
              disabled={pending}
              onClick={() => startTransition(() => runFraudAssessmentAction(claim.claim_ref))}
            >
              {pending ? "Re-running…" : "Re-run screening"}
            </button>
          )}
        </div>
      </div>

      {!latest && <p className="text-sm text-black/50">No fraud assessment has been run for this claim yet.</p>}

      {latest && (
        <div className="card space-y-4 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-3xl font-extrabold text-brand-ink">{latest.score}</span>
            <span className="text-sm text-black/45">/ 100</span>
            <Badge tone={bandTone(latest.risk_band)}>{latest.risk_band} risk</Badge>
            <StatusBadge status={latest.review_status} />
          </div>
          <p className="text-sm text-black/70">{latest.recommended_action}</p>

          <div>
            <p className="mb-2 text-xs font-bold uppercase text-black/45">
              Triggered indicators ({indicators.length})
            </p>
            {indicators.length === 0 && (
              <p className="text-sm text-black/50">No fraud indicators were triggered.</p>
            )}
            <ul className="space-y-2">
              {indicators.map((ind) => (
                <li key={ind.code} className="rounded-lg border border-black/10 p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-brand-ink">{ind.label}</span>
                    <span className="text-xs text-black/45">+{ind.weight} pts</span>
                  </div>
                  <p className="mt-1 text-xs text-black/55">{ind.detail}</p>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-xs text-black/40">
            Computed {new Date(latest.computed_at).toLocaleString()} by {latest.computed_by}
          </p>

          {latest.review_status === "reviewed" && (
            <div className="rounded-lg bg-black/5 p-3 text-sm">
              <p>
                <strong>Reviewed by:</strong> {latest.reviewed_by} on{" "}
                {latest.reviewed_at ? new Date(latest.reviewed_at).toLocaleString() : "—"}
              </p>
              <p>
                <strong>Decision:</strong> {latest.review_decision}
              </p>
              {latest.review_note && <p className="mt-1 text-black/60">{latest.review_note}</p>}
            </div>
          )}

          {canReview && latest.review_status === "pending_review" && (
            <form action={reviewFraudAssessmentAction} className="space-y-3 rounded-lg border border-black/10 p-4">
              <p className="text-xs font-bold uppercase text-black/45">Human review decision</p>
              <input type="hidden" name="claim_ref" value={claim.claim_ref} />
              <input type="hidden" name="assessment_id" value={latest.assessment_id} />
              <div>
                <label className="field-label">Decision</label>
                <select name="decision" className="field-input" defaultValue="proceed">
                  <option value="proceed">Proceed to investigation &amp; assessment</option>
                  <option value="escalate_to_investigator">Escalate to investigator</option>
                  <option value="cleared">Cleared — no fraud concern</option>
                </select>
              </div>
              <div>
                <label className="field-label">Review note</label>
                <textarea name="review_note" rows={2} className="field-input" placeholder="Rationale for this decision…" />
              </div>
              <button className="btn-primary">Record decision</button>
            </form>
          )}
        </div>
      )}

      {assessments.length > 1 && (
        <div>
          <p className="mb-2 text-xs font-bold uppercase text-black/45">Assessment history</p>
          <ul className="space-y-1 text-xs text-black/55">
            {assessments.slice(1).map((a) => (
              <li key={a.assessment_id}>
                {new Date(a.computed_at).toLocaleString()} — score {a.score} ({a.risk_band})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
