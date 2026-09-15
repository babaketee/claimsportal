import Link from "next/link";
import * as repo from "@/lib/repo";
import { SectionHeading } from "@/components/ui/Card";
import { StatCard, kes } from "@/components/ui/Stat";
import { StatusBadge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { submitBidAction } from "@/app/actions/claims";

export function SparePartsDashboard({ fullName }: { fullName: string }) {
  const openRfqs = repo.listOpenRfqs();
  const myBids = repo.getBidsByProvider(fullName);
  const won = myBids.filter((b) => b.status === "won");

  return (
    <div>
      <SectionHeading title="Spare Parts Provider Portal" subtitle="Open RFQs and your bid history" />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Open RFQs" value={String(openRfqs.length)} />
        <StatCard label="Bids submitted" value={String(myBids.length)} />
        <StatCard label="Won" value={String(won.length)} tone="red" />
        <StatCard label="Won value" value={kes(won.reduce((s, b) => s + b.unit_price, 0))} />
      </div>

      <h3 className="mb-3 text-sm font-bold">Open RFQs — submit a bid</h3>
      <div className="mb-8 space-y-4">
        {openRfqs.length === 0 && (
          <div className="card p-6 text-sm text-black/40">No open RFQs right now.</div>
        )}
        {openRfqs.map((rfq) => (
          <div key={rfq.rfq_ref} className="card p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="font-mono text-xs text-black/40">{rfq.rfq_ref}</p>
                <p className="text-sm font-bold">
                  {rfq.part_description} × {rfq.quantity} —{" "}
                  <Link href={`/app/claims/${rfq.claim_ref}`} className="text-brand-green hover:underline">
                    {rfq.claim_ref}
                  </Link>
                </p>
              </div>
              <StatusBadge status={rfq.status} />
            </div>
            <form action={submitBidAction} className="grid gap-2 sm:grid-cols-6">
              <input type="hidden" name="claim_ref" value={rfq.claim_ref} />
              <input type="hidden" name="rfq_ref" value={rfq.rfq_ref} />
              <input name="provider" defaultValue={fullName} required className="field-input sm:col-span-2" />
              <input name="brand" placeholder="Brand" required className="field-input" />
              <input name="condition" placeholder="Condition" required className="field-input" />
              <input name="unit_price" type="number" placeholder="Unit price" required className="field-input" />
              <input name="lead_days" type="number" placeholder="Lead days" required className="field-input" />
              <input name="warranty" placeholder="Warranty" className="field-input" />
              <input name="rating" type="number" step="0.1" min="1" max="5" defaultValue={4.5} className="field-input" />
              <button className="btn-primary sm:col-span-2">Submit Bid</button>
            </form>
          </div>
        ))}
      </div>

      <h3 className="mb-3 text-sm font-bold">My bids</h3>
      <Table
        columns={[
          { key: "rfq", label: "RFQ" },
          { key: "part", label: "Part" },
          { key: "price", label: "Price", align: "right" },
          { key: "status", label: "Status" },
        ]}
        rows={myBids.map((b) => ({
          rfq: (
            <Link href={`/app/claims/${b.rfq?.claim_ref}`} className="font-mono text-xs text-brand-green hover:underline">
              {b.rfq_ref}
            </Link>
          ),
          part: b.rfq?.part_description ?? "—",
          price: kes(b.unit_price),
          status: <StatusBadge status={b.status} />,
        }))}
        emptyLabel="No bids submitted yet."
      />
    </div>
  );
}
