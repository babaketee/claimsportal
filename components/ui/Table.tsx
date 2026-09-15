export function Table({
  columns,
  rows,
  emptyLabel = "Nothing here yet.",
}: {
  columns: { key: string; label: string; align?: "left" | "right" }[];
  rows: Record<string, React.ReactNode>[];
  emptyLabel?: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="card flex items-center justify-center p-10 text-sm text-black/40">
        {emptyLabel}
      </div>
    );
  }
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-black/5 bg-black/[0.02] text-xs uppercase tracking-wide text-black/45">
            {columns.map((c) => (
              <th
                key={c.key}
                className={`px-4 py-3 font-semibold ${c.align === "right" ? "text-right" : "text-left"}`}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-black/5 last:border-0 hover:bg-brand-green-10/30">
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 ${c.align === "right" ? "text-right" : "text-left"}`}>
                  {row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
