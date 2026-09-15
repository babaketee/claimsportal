import clsx from "clsx";

const STATUS_STYLES: Record<string, string> = {
  Draft: "bg-black/5 text-black/60",
  Submitted: "bg-blue-100 text-blue-700",
  "Under triage": "bg-amber-100 text-amber-700",
  "Under investigation and assessment": "bg-amber-100 text-amber-700",
  "On hold - awaiting information": "bg-brand-red-10 text-brand-red-dark",
  "Pending approval": "bg-blue-100 text-blue-700",
  Approved: "bg-brand-green-10 text-brand-green",
  Repudiated: "bg-brand-red-10 text-brand-red-dark",
  "Under repair": "bg-amber-100 text-amber-700",
  "Awaiting reinspection": "bg-amber-100 text-amber-700",
  "Pending payment": "bg-blue-100 text-blue-700",
  Paid: "bg-brand-green text-white",
  Closed: "bg-black/5 text-black/60",
  Reopened: "bg-brand-red-10 text-brand-red-dark",
  Withdrawn: "bg-black/5 text-black/50",
  Low: "bg-brand-green-10 text-brand-green",
  Medium: "bg-amber-100 text-amber-700",
  High: "bg-brand-red-10 text-brand-red-dark",
  pending: "bg-amber-100 text-amber-700",
  pending_review: "bg-amber-100 text-amber-700",
  reviewed: "bg-brand-green-10 text-brand-green",
  pending_approval: "bg-amber-100 text-amber-700",
  approved: "bg-brand-green-10 text-brand-green",
  released: "bg-black/5 text-black/60",
  accepted: "bg-blue-100 text-blue-700",
  completed: "bg-brand-green text-white",
  rejected: "bg-brand-red-10 text-brand-red-dark",
  paid: "bg-brand-green text-white",
  cancelled: "bg-black/5 text-black/50",
  open: "bg-amber-100 text-amber-700",
  done: "bg-brand-green-10 text-brand-green",
  overdue: "bg-brand-red-10 text-brand-red-dark",
  won: "bg-brand-green text-white",
  lost: "bg-black/5 text-black/50",
  submitted: "bg-blue-100 text-blue-700",
  not_configured: "bg-black/5 text-black/50",
  declined: "bg-brand-red-10 text-brand-red-dark",
  expired: "bg-black/5 text-black/50",
};

const URGENCY_STYLES: Record<string, string> = {
  High: "bg-brand-red-10 text-brand-red-dark",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-brand-green-10 text-brand-green",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx("badge", STATUS_STYLES[status] ?? "bg-black/5 text-black/60")}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function UrgencyBadge({ urgency }: { urgency: string }) {
  return (
    <span className={clsx("badge", URGENCY_STYLES[urgency] ?? "bg-black/5 text-black/60")}>
      {urgency}
    </span>
  );
}

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "green" | "red" | "amber" | "blue" }) {
  const tones: Record<string, string> = {
    neutral: "bg-black/5 text-black/60",
    green: "bg-brand-green-10 text-brand-green",
    red: "bg-brand-red-10 text-brand-red-dark",
    amber: "bg-amber-100 text-amber-700",
    blue: "bg-blue-100 text-blue-700",
  };
  return <span className={clsx("badge", tones[tone])}>{children}</span>;
}
