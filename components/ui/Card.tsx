import clsx from "clsx";

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("card p-5", className)}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className="text-sm font-bold text-brand-ink">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

export function SectionHeading({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-extrabold text-brand-green">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-black/50">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ label }: { label: string }) {
  return (
    <div className="card flex items-center justify-center p-10 text-sm text-black/40">{label}</div>
  );
}
