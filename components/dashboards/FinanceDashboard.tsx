import Link from "next/link";
import * as repo from "@/lib/repo";
import { SectionHeading } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { Table } from "@/components/ui/Table";
import { markSettlementPaidAction } from "@/app/actions/claims";

export function FinanceDashboard() {
  const approved = repo.getSettlementsByStatus("approved");
  const paid = repo.getSettlementsByStatus("paid");
  const pending = repo.getSettlementsByStatus("pending");
  const totalPayable = approved.reduce((s, x) => s + x.net_amount, 0);
  const totalPaidYtd = paid
    .filter((p) => (p.paid_at ?? "").startsWith(String(new Date().getFullYear())))
    .reduce((s, x) => s + x.net_amount, 0);

  return (
    <div>
      <SectionHeading title="Finance / Accounts Payable" subtitle="Approved settlements ready for payment" />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Awaiting payment" value={String(approved.length)} tone="red" />
        <StatCard label="Payable now" value={kes(totalPayable)} tone="red" />
        <StatCard label="Paid this year" value={kes(totalPaidYtd)} />
        <StatCard label="Recommendations pending HoC" value={String(pending.length)} />
      </div>

      <h3 className="mb-3 text-sm font-bold">Release payment</h3>
      <p className="mb-3 text-xs text-black/50">
        Payment is blocked until the claimant&apos;s discharge voucher has been signed (see the claim&apos;s
        E-Signatures tab) — a hard precondition per the workflow design (recommendation R5).
      </p>
      <Table
        columns={[
          { key: "ref", label: "Claim" },
          { key: "payee", label: "Payee" },
          { key: "gross", label: "Gross", align: "right" },
          { key: "wht", label: "WHT", align: "right" },
          { key: "net", label: "Net", align: "right" },
          { key: "action", label: "" },
        ]}
        rows={approved.map((s) => ({
          ref: (
            <Link href={`/app/claims/${s.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
              {s.claim_ref}
            </Link>
          ),
          payee: `${s.payee_name} (${s.payee_type})`,
          gross: kes(s.amount),
          wht: kes(s.wht_amount),
          net: <span className="font-semibold">{kes(s.net_amount)}</span>,
          action: (
            <form action={markSettlementPaidAction} className="flex items-center justify-end gap-1">
              <input type="hidden" name="claim_ref" value={s.claim_ref} />
              <input type="hidden" name="settlement_id" value={s.settlement_id} />
              <input name="bank_ref" placeholder="Bank ref" required className="field-input !w-28 !py-1 !text-xs" />
              <button className="btn-primary !px-3 !py-1.5 text-xs">Pay</button>
            </form>
          ),
        }))}
        emptyLabel="Nothing awaiting payment."
      />

      <h3 className="mb-3 mt-8 text-sm font-bold">Recent payments</h3>
      <Table
        columns={[
          { key: "ref", label: "Claim" },
          { key: "payee", label: "Payee" },
          { key: "net", label: "Net paid", align: "right" },
          { key: "bank", label: "Bank ref" },
          { key: "when", label: "Paid" },
        ]}
        rows={paid.slice(0, 20).map((s) => ({
          ref: (
            <Link href={`/app/claims/${s.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
              {s.claim_ref}
            </Link>
          ),
          payee: `${s.payee_name} (${s.payee_type})`,
          net: kes(s.net_amount),
          bank: s.bank_ref ?? "—",
          when: s.paid_at ? new Date(s.paid_at).toLocaleDateString() : "—",
        }))}
        emptyLabel="No payments recorded yet."
      />
    </div>
  );
}
