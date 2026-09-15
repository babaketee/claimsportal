"use client";

import { useState, useTransition } from "react";
import { DocusealForm } from "@docuseal/react";
import { requestSignatureAction, markSignedDemoAction } from "@/app/actions/docuseal";
import { StatusBadge } from "./ui/Badge";
import type { ClaimFormKey, DocusealSubmission, DocusealWorkflow } from "@/lib/types";
import { DOCUSEAL_WORKFLOW_LABELS } from "@/lib/types";
import type { ClaimFormDefinition } from "@/lib/claim-forms";

export function DocusealPanel({
  claimRef,
  workflow,
  formKey,
  formDefinition,
  configured,
  submissions,
  defaultSignerName,
  defaultSignerEmail,
  description,
}: {
  claimRef: string;
  workflow: DocusealWorkflow;
  formKey?: ClaimFormKey | null;
  formDefinition?: ClaimFormDefinition;
  configured: boolean;
  submissions: DocusealSubmission[];
  defaultSignerName: string;
  defaultSignerEmail: string;
  description: string;
}) {
  const [name, setName] = useState(defaultSignerName);
  const [email, setEmail] = useState(defaultSignerEmail);
  const [pending, startTransition] = useTransition();
  const [showForm, setShowForm] = useState(false);

  const latest = submissions[0];

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 rounded-lg bg-brand-green-10/50 p-4">
        <div>
          <p className="text-sm font-bold text-brand-green">
            {DOCUSEAL_WORKFLOW_LABELS[workflow]}
          </p>
          <p className="mt-1 text-xs text-black/55">{description}</p>
          {!configured && (
            <p className="mt-2 text-xs font-medium text-brand-red-dark">
              DocuSeal isn&apos;t configured for this document type yet — set DOCUSEAL_HOST,
              DOCUSEAL_API_KEY and the matching template id in .env.local to enable live
              signing. The demo flow below still tracks the step.
            </p>
          )}
        </div>
        {latest && <StatusBadge status={latest.status} />}
      </div>

      {formDefinition && !latest && (
        <details className="rounded-lg border border-black/10 p-4 text-sm">
          <summary className="cursor-pointer font-semibold text-brand-ink">
            {formDefinition.title} — form fields ({formDefinition.sourceDocument})
          </summary>
          <p className="mt-2 text-xs text-black/55">{formDefinition.description}</p>
          <div className="mt-3 space-y-3">
            {formDefinition.sections.map((section) => (
              <div key={section.title}>
                <p className="text-xs font-bold uppercase text-black/45">{section.title}</p>
                <ul className="mt-1 grid gap-x-4 gap-y-0.5 text-xs text-black/65 sm:grid-cols-2">
                  {section.fields.map((f) => (
                    <li key={f.name}>
                      {f.label}
                      {f.required && <span className="text-brand-red">*</span>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
            <div>
              <p className="font-bold text-black/45">Mandatory documents</p>
              <p className="text-black/60">{formDefinition.mandatoryDocuments.join(", ")}</p>
            </div>
            <div>
              <p className="font-bold text-black/45">Conditional documents</p>
              <p className="text-black/60">{formDefinition.conditionalDocuments.join(", ") || "None"}</p>
            </div>
          </div>
        </details>
      )}

      {!latest && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="field-label">Signer name</label>
            <input
              className="field-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="field-label">Signer email</label>
            <input
              className="field-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <button
              className="btn-primary"
              disabled={pending || !name.trim() || !email.trim()}
              onClick={() =>
                startTransition(() =>
                  requestSignatureAction({
                    claim_ref: claimRef,
                    workflow,
                    form_key: formKey,
                    signer_name: name.trim(),
                    signer_email: email.trim(),
                  })
                )
              }
            >
              {pending ? "Sending…" : "Send for e-signature"}
            </button>
          </div>
        </div>
      )}

      {latest && latest.status !== "completed" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3 text-sm text-black/60">
            <span>
              Sent to <strong className="text-brand-ink">{latest.signer_name}</strong> (
              {latest.signer_email})
            </span>
            <span className="text-black/30">·</span>
            <span>{new Date(latest.created_at).toLocaleString()}</span>
          </div>

          {latest.embed_src ? (
            <div className="overflow-hidden rounded-xl2 border border-black/10">
              {showForm ? (
                <DocusealForm
                  src={latest.embed_src}
                  email={latest.signer_email}
                  onComplete={() => markSignedDemoAction(latest.submission_id, claimRef)}
                />
              ) : (
                <div className="flex flex-col items-center gap-3 p-8 text-center">
                  <p className="text-sm text-black/60">Signing form ready.</p>
                  <button className="btn-secondary" onClick={() => setShowForm(true)}>
                    Open signing form
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-black/15 p-5 text-center">
              <p className="text-sm text-black/55">
                Demo mode: no live DocuSeal instance is configured, so there&apos;s no signing
                link to embed. Once real signing has happened, mark this step complete to
                continue the claim workflow.
              </p>
              <button
                className="btn-ghost mt-3"
                disabled={pending}
                onClick={() =>
                  startTransition(() => markSignedDemoAction(latest.submission_id, claimRef))
                }
              >
                {pending ? "Saving…" : "Mark as signed (demo)"}
              </button>
            </div>
          )}
        </div>
      )}

      {latest && latest.status === "completed" && (
        <div className="rounded-lg bg-brand-green-10 p-4 text-sm text-brand-green">
          ✔ Signed by {latest.signer_name} on{" "}
          {latest.completed_at ? new Date(latest.completed_at).toLocaleString() : "—"}
        </div>
      )}
    </div>
  );
}
