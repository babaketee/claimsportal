import { CLAIM_STATUSES } from "@/lib/types";

export function FilterBar({
  basePath,
  status,
  category,
  q,
  statuses = CLAIM_STATUSES,
}: {
  basePath: string;
  status?: string;
  category?: string;
  q?: string;
  statuses?: string[];
}) {
  return (
    <form action={basePath} className="card mb-5 flex flex-wrap items-end gap-3 p-4">
      <div>
        <label className="field-label">Status</label>
        <select name="status" defaultValue={status ?? "All"} className="field-input">
          <option value="All">All</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="field-label">Category</label>
        <select name="category" defaultValue={category ?? "All"} className="field-input">
          <option value="All">All</option>
          <option value="Motor">Motor</option>
          <option value="Business">Business</option>
        </select>
      </div>
      <div className="min-w-[180px] flex-1">
        <label className="field-label">Search ref / client / plate</label>
        <input name="q" defaultValue={q ?? ""} className="field-input" placeholder="CLM-2025…" />
      </div>
      <button className="btn-secondary">Filter</button>
    </form>
  );
}
