"use client";

import { useFormState, useFormStatus } from "react-dom";
import { loginAction, type LoginState } from "@/app/actions/auth";

const DEMO_ROWS: { email: string; password: string; role: string }[] = [
  { email: "client@insure.demo", password: "Assured#99", role: "Policyholder" },
  { email: "officer@insure.demo", password: "Handler#99", role: "Claims Officer" },
  { email: "hoc@insure.demo", password: "Oversee#99", role: "Head of Claims" },
  { email: "assessor@insure.demo", password: "Survey#99", role: "Assessor" },
  { email: "garage@insure.demo", password: "Wrench#99", role: "Garage" },
  { email: "investigator@insure.demo", password: "Sleuth#99", role: "Investigator" },
  { email: "finance@insure.demo", password: "Invoice#99", role: "Finance" },
  { email: "cfo@insure.demo", password: "Reserves#99", role: "Finance Head" },
  { email: "spares@insure.demo", password: "Catalog#99", role: "Spare Parts" },
  { email: "legal@insure.demo", password: "Counsel#99", role: "Legal" },
  { email: "admin@insure.demo", password: "SysCtrl#99", role: "Admin" },
  { email: "super@insure.demo", password: "Super#99", role: "Super Admin" },
];

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className="btn-primary w-full" disabled={pending}>
      {pending ? "Signing in…" : "Sign In"}
    </button>
  );
}

export function LoginForm() {
  const [state, formAction] = useFormState<LoginState, FormData>(loginAction, {});

  return (
    <div className="grid w-full gap-8 md:grid-cols-2 md:items-center">
      <form action={formAction} className="card animate-slide-up space-y-4 p-8">
        <div>
          <label className="field-label" htmlFor="identifier">
            Email Address / Policy Number
          </label>
          <input
            id="identifier"
            name="identifier"
            className="field-input"
            placeholder="you@insure.demo"
            autoComplete="username"
          />
        </div>
        <div>
          <label className="field-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            className="field-input"
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </div>
        {state.error && (
          <p className="rounded-lg bg-brand-red-10 px-3 py-2 text-sm font-medium text-brand-red-dark">
            {state.error}
          </p>
        )}
        <SubmitButton />
      </form>

      <div className="card animate-fade-in bg-brand-green-10/60 p-6">
        <p className="mb-3 text-sm font-semibold text-brand-green">Demo accounts — one per role</p>
        <div className="max-h-80 overflow-y-auto rounded-lg border border-black/5">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-white">
              <tr className="text-black/50">
                <th className="px-3 py-2 font-semibold">Role</th>
                <th className="px-3 py-2 font-semibold">Email</th>
                <th className="px-3 py-2 font-semibold">Password</th>
              </tr>
            </thead>
            <tbody>
              {DEMO_ROWS.map((r) => (
                <tr key={r.email} className="border-t border-black/5 bg-white/70">
                  <td className="px-3 py-1.5 font-medium text-brand-ink">{r.role}</td>
                  <td className="px-3 py-1.5 font-mono text-brand-green">{r.email}</td>
                  <td className="px-3 py-1.5 font-mono">{r.password}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[11px] text-black/40">
          Demo credentials only — replace with real auth (SSO / OTP / core IMS) before production.
        </p>
      </div>
    </div>
  );
}
