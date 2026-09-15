"use server";

import { revalidatePath } from "next/cache";
import { requireSession } from "@/lib/session";
import { createDocusealSubmission, isDocusealConfigured, templateIdFor } from "@/lib/docuseal";
import { createDocusealRecord, markDocusealCompleted, logCommunication } from "@/lib/repo";
import type { ClaimFormKey, DocusealWorkflow } from "@/lib/types";

export async function requestSignatureAction(input: {
  claim_ref: string;
  workflow: DocusealWorkflow;
  form_key?: ClaimFormKey | null;
  signer_name: string;
  signer_email: string;
}) {
  const session = await requireSession();

  if (isDocusealConfigured(input.workflow, input.form_key)) {
    const result = await createDocusealSubmission({
      workflow: input.workflow,
      formKey: input.form_key,
      signerName: input.signer_name,
      signerEmail: input.signer_email,
      metadata: { claim_ref: input.claim_ref },
    });
    createDocusealRecord({
      claim_ref: input.claim_ref,
      workflow: input.workflow,
      form_key: input.form_key,
      template_id: templateIdFor(input.workflow, input.form_key),
      docuseal_submission_id: result.docuseal_submission_id,
      signer_name: input.signer_name,
      signer_email: input.signer_email,
      status: result.ok ? "pending" : "not_configured",
      embed_src: result.embed_src,
      created_by: session.email,
    });
  } else {
    // Demo mode — no real DocuSeal instance reachable yet.
    createDocusealRecord({
      claim_ref: input.claim_ref,
      workflow: input.workflow,
      form_key: input.form_key,
      template_id: templateIdFor(input.workflow, input.form_key),
      docuseal_submission_id: null,
      signer_name: input.signer_name,
      signer_email: input.signer_email,
      status: "not_configured",
      embed_src: null,
      created_by: session.email,
    });
  }

  logCommunication({
    claim_ref: input.claim_ref,
    channel: "email",
    direction: "outbound",
    summary: `E-signature request sent (${input.workflow.replace(/_/g, " ")}) to ${input.signer_name}`,
    created_by: session.email,
    contact_name: input.signer_name,
    contact_phone: input.signer_email,
  });

  revalidatePath(`/app/claims/${input.claim_ref}`);
}

export async function markSignedDemoAction(submission_id: string, claim_ref: string) {
  await requireSession();
  markDocusealCompleted(submission_id);
  revalidatePath(`/app/claims/${claim_ref}`);
}
