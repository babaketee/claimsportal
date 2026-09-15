import "server-only";
import type { ClaimFormKey, DocusealWorkflow } from "./types";

// ---------------------------------------------------------------------------
// DocuSeal integration — self-hosted e-signature.
//
// Configure via env vars (see .env.example):
//   DOCUSEAL_HOST     e.g. docuseal.definiteassurance.co.ke (no protocol/slash)
//   DOCUSEAL_API_KEY  from DocuSeal → Settings → API
//   DOCUSEAL_TEMPLATE_<WORKFLOW>  numeric template id per document type
//
// When any of these are missing for a given workflow, the app runs that
// workflow in "not configured" demo mode: the UI explains what's missing and
// lets the reviewer mark the step complete locally so the rest of the claim
// lifecycle can still be demoed end-to-end.
// ---------------------------------------------------------------------------

const SIMPLE_TEMPLATE_ENV: Partial<Record<DocusealWorkflow, string | undefined>> = {
  settlement_discharge: process.env.DOCUSEAL_TEMPLATE_SETTLEMENT_DISCHARGE,
  demand_letter: process.env.DOCUSEAL_TEMPLATE_DEMAND_LETTER,
  engagement_letter: process.env.DOCUSEAL_TEMPLATE_ENGAGEMENT_LETTER,
};

// The claim_form workflow has one DocuSeal template per source paper form
// (see lib/claim-forms.ts), each configured via its own env var so an
// insurer can wire up the 7 real templates independently as they're built
// in their self-hosted DocuSeal instance.
const FORM_TEMPLATE_ENV: Record<ClaimFormKey, string | undefined> = {
  motor_accident: process.env.DOCUSEAL_TEMPLATE_FORM_MOTOR_ACCIDENT,
  windscreen: process.env.DOCUSEAL_TEMPLATE_FORM_WINDSCREEN,
  all_risks: process.env.DOCUSEAL_TEMPLATE_FORM_ALL_RISKS,
  baggage_property: process.env.DOCUSEAL_TEMPLATE_FORM_BAGGAGE_PROPERTY,
  wiba: process.env.DOCUSEAL_TEMPLATE_FORM_WIBA,
  personal_accident: process.env.DOCUSEAL_TEMPLATE_FORM_PERSONAL_ACCIDENT,
  investigator_notification: process.env.DOCUSEAL_TEMPLATE_FORM_INVESTIGATOR_NOTIFICATION,
  general_claim: process.env.DOCUSEAL_TEMPLATE_FORM_GENERAL_CLAIM,
};

export function docusealHost(): string | null {
  const host = process.env.DOCUSEAL_HOST?.trim();
  return host ? host.replace(/\/$/, "").replace(/^https?:\/\//, "") : null;
}

export function isDocusealConfigured(workflow: DocusealWorkflow, formKey?: ClaimFormKey | null): boolean {
  const templateId =
    workflow === "claim_form" ? (formKey ? FORM_TEMPLATE_ENV[formKey] : undefined) : SIMPLE_TEMPLATE_ENV[workflow];
  return Boolean(docusealHost() && process.env.DOCUSEAL_API_KEY && templateId);
}

export function templateIdFor(workflow: DocusealWorkflow, formKey?: ClaimFormKey | null): string | null {
  if (workflow === "claim_form") return (formKey ? FORM_TEMPLATE_ENV[formKey] : undefined) ?? null;
  return SIMPLE_TEMPLATE_ENV[workflow] ?? null;
}

interface DocusealSubmitter {
  slug: string;
  email: string;
  name?: string | null;
}

interface CreateSubmissionResult {
  ok: boolean;
  docuseal_submission_id: string | null;
  embed_src: string | null;
  error?: string;
}

/**
 * Create a DocuSeal submission for a template and return the embeddable
 * signing URL for the first (and in our flows, only) submitter.
 */
export async function createDocusealSubmission(params: {
  workflow: DocusealWorkflow;
  formKey?: ClaimFormKey | null;
  signerName: string;
  signerEmail: string;
  metadata?: Record<string, string>;
}): Promise<CreateSubmissionResult> {
  const host = docusealHost();
  const apiKey = process.env.DOCUSEAL_API_KEY;
  const templateId = templateIdFor(params.workflow, params.formKey);

  if (!host || !apiKey || !templateId) {
    return {
      ok: false,
      docuseal_submission_id: null,
      embed_src: null,
      error: "DocuSeal is not configured for this workflow yet.",
    };
  }

  try {
    const res = await fetch(`https://${host}/api/submissions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Auth-Token": apiKey,
      },
      body: JSON.stringify({
        template_id: Number.isNaN(Number(templateId)) ? templateId : Number(templateId),
        send_email: false,
        submitters: [{ name: params.signerName, email: params.signerEmail }],
        metadata: params.metadata ?? {},
      }),
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return {
        ok: false,
        docuseal_submission_id: null,
        embed_src: null,
        error: `DocuSeal API error (${res.status}): ${text.slice(0, 300)}`,
      };
    }

    const data = (await res.json()) as DocusealSubmitter[] | { error?: string };
    if (!Array.isArray(data) || data.length === 0) {
      return {
        ok: false,
        docuseal_submission_id: null,
        embed_src: null,
        error: "DocuSeal did not return a submitter slug.",
      };
    }

    const submitter = data[0];
    return {
      ok: true,
      docuseal_submission_id: String((submitter as unknown as { submission_id?: number }).submission_id ?? submitter.slug),
      embed_src: `https://${host}/s/${submitter.slug}`,
    };
  } catch (err) {
    return {
      ok: false,
      docuseal_submission_id: null,
      embed_src: null,
      error: err instanceof Error ? err.message : "Unknown error contacting DocuSeal.",
    };
  }
}
