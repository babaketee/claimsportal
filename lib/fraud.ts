// Note: no "server-only" import here — this module is also loaded directly
// by scripts/seed.ts via tsx, outside of Next's bundler.
import * as repo from "./repo";
import { getFraudThresholds, getFraudFrequencyConfig } from "./config";
import { formDefinitionFor } from "./claim-forms";
import type { FraudIndicator, FraudRiskBand } from "./types";

// ---------------------------------------------------------------------------
// AI-assisted fraud screening & triage (design doc Stage 5).
//
// This is a deterministic, explainable rules engine rather than a black-box
// model: every point on the score is traceable to a named indicator, which
// matters for an insurance regulator and for the human reviewer who must be
// able to see *why* a claim was flagged. It mirrors the two properties the
// design document insists on for this stage:
//   - it SCORES AND ROUTES ONLY — it never approves or declines a claim;
//   - when it can't run (e.g. missing data), the claim falls back to normal
//     manual triage rather than blocking the workflow.
// ---------------------------------------------------------------------------

function daysBetween(a: string, b: string): number {
  const ms = new Date(a).getTime() - new Date(b).getTime();
  return Math.round(ms / 86400000);
}

export async function runFraudScreening(
  claim_ref: string,
  computed_by = "system"
): Promise<{ score: number; band: FraudRiskBand; indicators: FraudIndicator[] } | null> {
  const claim = repo.getClaim(claim_ref);
  if (!claim) return null;

  const indicators: FraudIndicator[] = [];
  const thresholds = getFraudThresholds();
  const freqCfg = getFraudFrequencyConfig();

  // 1. Claim frequency — repeat claims by the same client / policy.
  const related = repo
    .getClaimsForClientOrPolicy(claim.client_email, claim.policy_number, claim_ref)
    .filter((c) => Math.abs(daysBetween(claim.date_reported, c.date_reported)) <= freqCfg.windowDays);
  if (related.length + 1 >= freqCfg.claimCountFlag) {
    indicators.push({
      code: "claim_frequency",
      label: "Elevated claim frequency",
      weight: 25,
      detail: `${related.length + 1} claims (including this one) from the same client/policy within ${freqCfg.windowDays} days.`,
    });
  }

  // 2. Duplicate / recycled loss — same vehicle, overlapping report window.
  if (claim.vehicle_reg) {
    const sameVehicle = repo
      .getClaimsForVehicle(claim.vehicle_reg, claim_ref)
      .filter((c) => Math.abs(daysBetween(claim.date_reported, c.date_reported)) <= 60);
    if (sameVehicle.length > 0) {
      indicators.push({
        code: "duplicate_vehicle",
        label: "Same vehicle claimed twice in a short window",
        weight: 25,
        detail: `Vehicle ${claim.vehicle_reg} appears on ${sameVehicle.length} other claim(s) within 60 days.`,
      });
    }
  }

  // 3. Claim amount vs. category average.
  const avg = repo.avgAmountForType(claim.claim_type, claim_ref);
  if (avg > 0 && claim.claim_amount > avg * 2) {
    indicators.push({
      code: "amount_outlier",
      label: "Claim amount is a significant outlier for this claim type",
      weight: 15,
      detail: `Claimed KES ${claim.claim_amount.toLocaleString()} vs. an average of KES ${Math.round(avg).toLocaleString()} for "${claim.claim_type}" claims.`,
    });
  }

  // 4. Round-number claim amount.
  if (claim.claim_amount > 0 && claim.claim_amount % 10000 === 0) {
    indicators.push({
      code: "round_amount",
      label: "Suspiciously round claim amount",
      weight: 5,
      detail: `KES ${claim.claim_amount.toLocaleString()} is an exact multiple of 10,000.`,
    });
  }

  // 5. Reporting delay — long gap between loss and notification.
  if (claim.date_of_loss) {
    const delay = daysBetween(claim.date_reported, claim.date_of_loss);
    if (delay > 30) {
      indicators.push({
        code: "reporting_delay",
        label: "Late notification of loss",
        weight: 10,
        detail: `Reported ${delay} days after the claimed loss date (policy typically expects prompt notification).`,
      });
    }
  }

  // 6. Photo / evidence metadata — EXIF capture-date and GPS mismatches.
  const docs = repo.getDocuments(claim_ref);
  const photoDocs = docs.filter((d) => d.exif_json);
  let exifMismatchCount = 0;
  let noMetadataCount = 0;
  for (const d of photoDocs) {
    try {
      const meta = JSON.parse(d.exif_json as string) as { flags: string[]; days_from_loss: number | null };
      if (meta.days_from_loss !== null && Math.abs(meta.days_from_loss) > 2) exifMismatchCount++;
      if (meta.flags?.some((f) => f.includes("No capture-date") || f.includes("No GPS"))) noMetadataCount++;
    } catch {
      /* ignore unparseable metadata */
    }
  }
  if (exifMismatchCount > 0) {
    indicators.push({
      code: "exif_date_mismatch",
      label: "Photo capture date does not match claimed loss date",
      weight: 20,
      detail: `${exifMismatchCount} uploaded photo(s) were captured more than 2 days from the claimed loss date — a possible staged or recycled loss photo.`,
    });
  }
  if (photoDocs.length > 0 && noMetadataCount === photoDocs.length) {
    indicators.push({
      code: "no_photo_metadata",
      label: "All uploaded photos are missing capture metadata",
      weight: 5,
      detail: "No EXIF date/location data could be read from any uploaded photo (stripped, screenshotted, or forwarded via messaging apps).",
    });
  }

  // 7. Missing mandatory documents for this claim type (Appendix C checklist).
  const form = formDefinitionFor(claim.claim_type);
  const uploadedTypes = new Set(docs.map((d) => d.doc_type));
  const missingMandatory = form.mandatoryDocuments.length > Math.min(docs.length, form.mandatoryDocuments.length)
    ? form.mandatoryDocuments.length - docs.length
    : 0;
  if (docs.length === 0) {
    indicators.push({
      code: "no_documents",
      label: "No supporting documents uploaded yet",
      weight: 10,
      detail: `Mandatory documents for "${claim.claim_type}" per the document checklist: ${form.mandatoryDocuments.join(", ")}.`,
    });
  } else if (missingMandatory > 0 && docs.length < form.mandatoryDocuments.length) {
    indicators.push({
      code: "incomplete_documents",
      label: "Fewer documents uploaded than the mandatory checklist requires",
      weight: 5,
      detail: `${docs.length} of ${form.mandatoryDocuments.length} mandatory document(s) for "${claim.claim_type}" appear to be on file.`,
    });
  }
  void uploadedTypes;

  // 8. Investigator-raised fraud suspicion — a direct, high-weight signal.
  const invReports = repo.getInvestigatorReports(claim_ref);
  const flagged = invReports.find((r) => r.fraud_suspected === "yes");
  if (flagged) {
    indicators.push({
      code: "investigator_flag",
      label: "Investigator reported suspected fraud indicators",
      weight: 30,
      detail: flagged.fraud_basis || "The assigned investigator flagged this claim on the Notification of Incident report.",
    });
  }

  const score = Math.max(0, Math.min(100, indicators.reduce((s, i) => s + i.weight, 0)));
  const band: FraudRiskBand = score >= thresholds.highFloor ? "High" : score >= thresholds.mediumFloor ? "Medium" : "Low";

  const recommended_action =
    band === "High"
      ? "Route to mandatory investigator review; hold pending-approval until cleared. AI never auto-declines — a human reviewer must confirm the outcome."
      : band === "Medium"
        ? "Route to standard investigation and assessment with a manual fraud-review checkpoint before approval."
        : "Continue standard triage; no additional fraud review required.";

  repo.createFraudAssessment({
    claim_ref,
    score,
    risk_band: band,
    indicators_json: JSON.stringify(indicators),
    recommended_action,
    computed_by,
  });

  return { score, band, indicators };
}

/**
 * Runs fraud screening for a freshly submitted claim and advances its status
 * out of "Submitted" into "Under triage", then into the appropriate next
 * stage based on the risk band — mirroring Stage 5 of the lifecycle. Also
 * pushes an initial reserve estimate, since the design principle is that
 * reserve movements should be pushed at every stage, not only at final
 * payout.
 */
export async function triageNewClaim(claim_ref: string) {
  const claim = repo.getClaim(claim_ref);
  if (!claim) return;

  repo.updateClaimStatus(claim_ref, "Under triage", "system", "Automated fraud screening & triage (Stage 5)");

  const result = await runFraudScreening(claim_ref, "system");

  if (claim.claim_amount > 0) {
    repo.setReserve({
      claim_ref,
      reserve_type: "initial",
      amount: Math.round(claim.claim_amount * 0.9),
      purpose: "Initial reserve set at triage (Stage 5), pending investigation/assessment",
      created_by: "system",
      note: "Auto-created on submission per configuration-driven reserve policy.",
    });
  }

  if (!result || result.band !== "High") {
    repo.updateClaimStatus(
      claim_ref,
      "Under investigation and assessment",
      "system",
      "Routed to parallel investigation & assessment (Stage 6)"
    );
    repo.addDiaryEntry({
      claim_ref,
      task: "Assign assessor / investigator and begin parallel investigation & assessment",
      due_date: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10),
      assigned_to: claim.assigned_officer ?? "",
      priority: "normal",
      created_by: "system",
    });
  } else {
    repo.updateClaimStatus(
      claim_ref,
      "On hold - awaiting information",
      "system",
      "High fraud-risk score — held for mandatory manual fraud review before proceeding (Stage 5 gate)"
    );
    repo.addDiaryEntry({
      claim_ref,
      task: "URGENT: Review high fraud-risk assessment before this claim proceeds",
      due_date: new Date().toISOString().slice(0, 10),
      assigned_to: "hoc@insure.demo",
      priority: "urgent",
      created_by: "system",
      note: "Automated fraud screening scored this claim High risk. A human reviewer must confirm before it can proceed.",
    });
  }
}
