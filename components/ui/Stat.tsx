import clsx from "clsx";

export function StatCard({
  label,
  value,
  hint,
  tone = "green",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "green" | "red" | "neutral";
}) {
  return (
    <div className="card animate-fade-in p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-black/45">{label}</p>
      <p
        className={clsx(
          "mt-1.5 text-2xl font-extrabold",
          tone === "green" && "text-brand-green",
          tone === "red" && "text-brand-red",
          tone === "neutral" && "text-brand-ink"
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-black/40">{hint}</p>}
    </div>
  );
}

export function kes(n: number): string {
  return `KES ${Math.round(n).toLocaleString("en-KE")}`;
}
